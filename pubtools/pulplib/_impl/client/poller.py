import os
import logging

from pubtools.pulplib._impl.model import Task
from .errors import MissingTaskException, TaskFailedException


LOG = logging.getLogger("pubtools.pulplib")

# need to catch exceptions and pass onto descriptors in several places
# pylint: disable=broad-except


class TaskPoller(object):
    # TODO: messages like these if there's no update for a while:
    # 2019-06-12 06:40:03 +0000 [DEBUG   ] Still waiting on Pulp, load: 1 running, 4 waiting

    MAX_ATTEMPTS = 60
    DELAY = 5.0

    def __init__(self, session, url):
        self.session = session
        self.url = url
        self.attempt = 1

    def __call__(self, descriptors):
        try:
            # Find every referenced Pulp task
            descriptor_task_ids, all_task_ids = self.gather_descriptor_tasks(
                descriptors
            )

            # Get status of all of those tasks from Pulp
            tasks = self.search_tasks(all_task_ids)

            # Now check all descriptors and decide which have completed
            self.resolve_descriptors(tasks, descriptor_task_ids)

            # Any success resets the retry counter
            self.attempt = 1
        except Exception:
            if self.attempt >= self.MAX_ATTEMPTS:
                LOG.exception("Pulp task polling repeatedly failed")
                raise

            LOG.warning(
                "Error occurred during Pulp task polling, will retry %d more time(s)",
                (self.MAX_ATTEMPTS - self.attempt),
                exc_info=1,
            )

            self.attempt += 1

        return self.DELAY

    def resolve_descriptors(self, tasks, descriptor_task_ids):
        for descriptor, task_ids in descriptor_task_ids:
            self.resolve_descriptor(tasks, descriptor, task_ids)

    def resolve_descriptor(self, tasks, descriptor, task_ids):
        out = []

        for task_id in task_ids:
            task = tasks.get(task_id)

            if not task:
                # A task has been lost somehow
                exception = MissingTaskException(
                    "Task %s disappeared from Pulp!" % task_id
                )
                LOG.warning("%s", exception)
                descriptor.yield_exception(exception)
                return

            if task.completed and not task.succeeded:
                exception = TaskFailedException(task)
                descriptor.yield_exception(exception)
                return

            out.append(task)

        for task in out:
            if not task.completed:
                # can't resolve the future yet since there's a pending task
                return

        # OK, future can be resolved with the completed tasks
        descriptor.yield_result(out)

    def search_tasks(self, task_ids):
        out = {}

        if not task_ids:
            return out

        search_url = os.path.join(self.url, "pulp/api/v2/tasks/search/")
        search = {"criteria": {"filters": {"task_id": {"$in": task_ids}}}}
        LOG.debug("Searching %s task(s) at %s", len(task_ids), search_url)
        LOG.debug("Search criteria: %s", search)

        response = self.session.post(search_url, json=search)

        try:
            response.raise_for_status()
        except Exception as ex:
            # raise_for_status exception info is a little terse.
            # Try to log response body as well if we can, but be prepared
            # for that to fail as well.
            try:
                LOG.warning("Pulp task search failure: %s", response.json())
            except Exception:
                pass
            raise ex

        for elem in response.json():
            task = Task.from_data(elem)
            out[task.id] = task

        return out

    def gather_descriptor_tasks(self, descriptors):
        descriptor_tasks = []
        all_tasks = []

        for descriptor in descriptors:
            result = descriptor.result
            try:
                tasks = result.get("spawned_tasks") or []
                task_ids = [t["task_id"] for t in tasks]
                descriptor_tasks.append((descriptor, task_ids))
                all_tasks.extend(task_ids)
            except Exception as ex:
                LOG.warning("Not a valid call report from Pulp: %s", result, exc_info=1)
                descriptor.yield_exception(ex)

        return descriptor_tasks, all_tasks
