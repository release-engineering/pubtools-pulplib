import random
import uuid
import threading

from collections import namedtuple

import six
from more_executors.futures import f_return, f_return_error

from pubtools.pulplib import Page, PulpException, Criteria, Task
from .. import compat_attr as attr

from .match import match_object

Publish = namedtuple("Publish", ["repository", "tasks"])


class FakeClient(object):
    _PAGE_SIZE = 3

    def __init__(self):
        self._repositories = []
        self._publish_history = []
        self._lock = threading.RLock()
        self._uuidgen = random.Random()
        self._uuidgen.seed(0)

    def search_repository(self, criteria=None):
        criteria = criteria or Criteria.true()
        repos = []

        try:
            for repo in self._repositories:
                if match_object(criteria, repo):
                    repos.append(self._attach(repo))
        except Exception as ex:  # pylint: disable=broad-except
            return f_return_error(ex)

        # callers should not make any assumption about the order of returned
        # values. Encourage that by returning output in unpredictable order
        random.shuffle(repos)

        # Split it into pages
        page_data = []
        current_page_data = []
        while repos:
            next_elem = repos.pop()
            current_page_data.append(next_elem)
            if len(current_page_data) == self._PAGE_SIZE and repos:
                page_data.append(current_page_data)
                current_page_data = []

        page_data.append(current_page_data)

        page = Page()
        next_page = None
        for batch in reversed(page_data):
            page = Page(data=batch, next=next_page)
            next_page = f_return(page)

        return f_return(page)

    def get_repository(self, repository_id):
        if not isinstance(repository_id, six.string_types):
            raise TypeError("Invalid argument: id=%s" % id)

        data = self.search_repository(Criteria.with_id(repository_id)).result().data
        if len(data) != 1:
            return f_return_error(
                PulpException("Repository id=%s not found" % repository_id)
            )

        return f_return(data[0])

    def _delete_resource(self, resource_type, resource_id):
        if resource_type == "repositories":
            return self._delete_repository(resource_id)

        # There is no way to get here using public API
        raise AssertionError(
            "Asked to delete unexpected %s" % resource_type
        )  # pragma: no cover

    def _delete_repository(self, repo_id):
        with self._lock:
            found = False
            for idx, repo in enumerate(self._repositories):
                if repo.id == repo_id:
                    found = True
                    break

            if not found:
                # Deleting something which already doesn't exist is fine
                return f_return([])

            self._repositories.pop(idx)  # pylint: disable=undefined-loop-variable
            return f_return(
                [Task(id=self._next_task_id(), completed=True, succeeded=True)]
            )

    def _publish_repository(self, repo, distributors_with_config):
        repo_f = self.get_repository(repo.id)
        if repo_f.exception():
            # Repo can't be found, let that exception propagate
            return repo_f

        tasks = []
        for _ in distributors_with_config:
            tasks.append(Task(id=self._next_task_id(), completed=True, succeeded=True))

        self._publish_history.append(Publish(repo, tasks))

        return f_return(tasks)

    def _attach(self, pulp_object):
        pulp_object = attr.evolve(pulp_object)
        pulp_object.__dict__["_client"] = self
        return pulp_object

    def _next_task_id(self):
        with self._lock:
            next_raw_id = self._uuidgen.randint(0, 2 ** 128)
        return str(uuid.UUID(int=next_raw_id))
