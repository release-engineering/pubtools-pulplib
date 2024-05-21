import os
import logging
import datetime
import threading

from pubtools.pulplib._impl.model import Task
from .errors import MissingTaskException, TaskFailedException


LOG = logging.getLogger("pubtools.pulplib")

# need to catch exceptions and pass onto descriptors in several places
# pylint: disable=broad-except


def task_log(task):
    parts = [task.id]
    for tag in task.tags or []:
        # All tags start with 'pulp:' prefix, which makes it useless noise
        # in the logs, so filter them out to save some horizontal space
        if tag.startswith("pulp:"):
            tag = tag[len("pulp:") :]
        parts.append(tag)
    return ", ".join(parts)


class TaskPoller(object):
    # Poll function used with PollExecutor.
    # Takes care of polling for Pulp task completion and resolving futures.

    # max number of times polling is attempted before errors are considered fatal
    MAX_ATTEMPTS = 60

    # delay in seconds between poll attempts
    DELAY = 5.0

    # delay in seconds between "Still waiting" log messages, if Pulp tasks
    # apparently are not being processed
    ACTIVITY_DELAY = datetime.timedelta(minutes=5)

    def __init__(self, session, url, timer=datetime.datetime.utcnow):
        self._session = session
        # Lock protects 'session', as cancel() may be called from one thread
        # while another is in the middle of poll, both using the session
        self.lock = threading.Lock()
        self.url = url
        self.attempt = 1
        self.timer = timer
        self.last_activity = self.timer()

    @property
    def session(self):
        # A helper to ensure all access to session is protected by lock.
        # If you try to use the requests.Session without the lock held,
        # it's a bug.
        assert self.lock.locked(), "INTERNAL ERROR: unsynchronized access to session"
        return self._session

    def __call__(self, descriptors):
        try:
            # Find every referenced Pulp task
            descriptor_task_ids, all_task_ids = self.gather_descriptor_tasks(
                descriptors
            )

            # Get status of all of those tasks from Pulp
            with self.lock:
                tasks = self.search_tasks(all_task_ids)

            # Now check all descriptors and decide which have completed
            resolved_count = self.resolve_descriptors(tasks, descriptor_task_ids)

            # Any successful poll resets the retry counter
            self.attempt = 1

            # We have activity if we resolved at least one thing (or if there was
            # nothing to do at all)
            if resolved_count or not descriptors:
                self.last_activity = self.timer()

            # If nothing's going on for a while, log about it
            with self.lock:
                self.log_if_inactive()
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
        resolved = 0
        for descriptor, task_ids in descriptor_task_ids:
            if self.resolve_descriptor(tasks, descriptor, task_ids):
                resolved += 1
        return resolved

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
                return True

            if task.completed and not task.succeeded:
                LOG.warning("Pulp task failed: %s", task_log(task))

                exception = TaskFailedException(task)
                descriptor.yield_exception(exception)
                return True

            out.append(task)

        for task in out:
            if not task.completed:
                # can't resolve the future yet since there's a pending task
                return False

            LOG.info("Pulp task completed: %s", task_log(task))

        # OK, future can be resolved with the completed tasks
        descriptor.yield_result(out)
        return True

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

    def cancel(self, task_data):
        # Invoked when a request is made to cancel a future.
        task_ids = [t["task_id"] for t in task_data["spawned_tasks"]]

        with self.lock:
            for task_id in task_ids:
                url = os.path.join(self.url, "pulp/api/v2/tasks/%s/" % task_id)
                response = self.session.delete(url)
                response.raise_for_status()

                LOG.info("Cancelled Pulp task: %s", task_id)

        return True

    def log_if_inactive(self):
        now = self.timer()
        delta = now - self.last_activity

        if delta < self.ACTIVITY_DELAY:
            # nothing to do (yet)
            return

        # We've been idle for too long, log a message to confirm we're not dead
        search_url = os.path.join(self.url, "pulp/api/v2/tasks/search/")
        search = {
            "criteria": {"filters": {"state": {"$in": ["running", "waiting"]}}},
            "fields": ["state"],
        }

        response = self.session.post(search_url, json=search)
        response.raise_for_status()
        tasks = response.json()

        running_count = len([t for t in tasks if t["state"] == "running"])
        waiting_count = len([t for t in tasks if t["state"] == "waiting"])

        LOG.info(
            "Still waiting on Pulp, load: %s running, %s waiting",
            running_count,
            waiting_count,
            extra={
                "event": {
                    "type": "awaiting-pulp",
                    "running-tasks": running_count,
                    "waiting-tasks": waiting_count,
                }
            },
        )

        # Logging that message counts as "activity"
        self.last_activity = now
