import random
import uuid
import threading
import hashlib
import json
import re

from collections import namedtuple

import six
from six.moves import StringIO

from more_executors.futures import f_return, f_return_error, f_flat_map, f_proxy

from pubtools.pulplib import (
    Page,
    PulpException,
    Criteria,
    Task,
    Repository,
    Distributor,
    Unit,
    MaintenanceReport,
)
from pubtools.pulplib._impl.client.search import search_for_criteria
from .. import compat_attr as attr

from .match import match_object

Publish = namedtuple("Publish", ["repository", "tasks"])
Upload = namedtuple("Upload", ["repository", "tasks", "name", "sha256"])
Sync = namedtuple("Sync", ["repository", "tasks", "sync_config"])


class FakeClient(object):  # pylint:disable = too-many-instance-attributes
    # Client implementation holding data in memory rather than
    # using a remote Pulp server.
    #
    # This class is not public, but it must have all of the same public
    # API as the pubtools.pulplib.Client class. The idea is that any code
    # written against pubtools.pulplib.Client should be able to work with
    # an instance of this class swapped in.
    _PAGE_SIZE = 3
    _DEFAULT_TYPE_IDS = [
        "distribution",
        "drpm",
        "erratum",
        "iso",
        "modulemd_defaults",
        "modulemd",
        "package_category",
        "package_environment",
        "package_group",
        "package_langpacks",
        "repository",
        "rpm",
        "srpm",
        "yum_repo_metadata_file",
    ]

    def __init__(self):
        self._repositories = []
        self._repo_units = {}
        self._publish_history = []
        self._upload_history = []
        self._sync_history = []
        self._maintenance_report = None
        self._type_ids = self._DEFAULT_TYPE_IDS[:]
        self._lock = threading.RLock()
        self._uuidgen = random.Random()
        self._uuidgen.seed(0)
        self._shutdown = False

    def __enter__(self):
        return self

    def __exit__(self, *_args, **_kwargs):
        self._shutdown = True

    def _ensure_alive(self):
        if self._shutdown:
            # We are technically capable of working just fine after shutdown,
            # but the point of this class is to be an accurate stand-in for
            # a real client, so raise the same kind of exception here
            raise RuntimeError("cannot schedule new futures after shutdown")

    def search_repository(self, criteria=None):
        self._ensure_alive()

        criteria = criteria or Criteria.true()
        repos = []

        # Pass the criteria through the code used by the real client to build
        # up the Pulp query. We don't actually *use* the resulting query since
        # we're not accessing a real Pulp server. The point is to ensure the
        # same validation and error behavior as used by the real client also
        # applies to the fake.
        search_for_criteria(criteria, Repository)

        try:
            for repo in self._repositories:
                if match_object(criteria, repo):
                    repos.append(self._attach_repo(repo))
        except Exception as ex:  # pylint: disable=broad-except
            return f_return_error(ex)

        # callers should not make any assumption about the order of returned
        # values. Encourage that by returning output in unpredictable order
        random.shuffle(repos)
        return self._prepare_pages(repos)

    def search_content(self, criteria=None):
        self._ensure_alive()

        criteria = criteria or Criteria.true()
        out = []

        # Pass the criteria through the code used by the real client to build
        # up the Pulp query. We don't actually *use* the resulting query since
        # we're not accessing a real Pulp server. The point is to ensure the
        # same validation and error behavior as used by the real client also
        # applies to the fake.
        prepared_search = search_for_criteria(criteria, Unit)

        available_type_ids = set(self._type_ids)
        missing_type_ids = set(prepared_search.type_ids or []) - available_type_ids
        if missing_type_ids:
            return f_return_error(
                PulpException(
                    "following type ids are not supported on the server: %s"
                    % ",".join(missing_type_ids)
                )
            )

        for unit in sum([list(x) for x in self._repo_units.values()], []):
            if (
                prepared_search.type_ids
                and unit.content_type_id not in prepared_search.type_ids
            ):
                continue
            if match_object(criteria, unit):
                out.append(unit)

        # callers should not make any assumption about the order of returned
        # values. Encourage that by returning output in unpredictable order
        random.shuffle(out)
        return self._prepare_pages(out)

    def search_distributor(self, criteria=None):
        self._ensure_alive()

        criteria = criteria or Criteria.true()
        distributors = []

        search_for_criteria(criteria, Distributor)

        try:
            for repo in self._repositories:
                for distributor in repo.distributors:
                    if match_object(criteria, distributor):
                        distributors.append(attr.evolve(distributor, repo_id=repo.id))
        except Exception as ex:  # pylint: disable=broad-except
            return f_return_error(ex)

        random.shuffle(distributors)
        return self._prepare_pages(distributors)

    def _search_repo_units(self, repo_id, criteria):
        criteria = criteria or Criteria.true()

        # Pass the criteria through the same handling as used by the real client
        # for serialization, to ensure we reject criteria also rejected by real client.
        # We don't actually use the result, this is only for validation.
        search_for_criteria(criteria, Unit)

        repo_f = self.get_repository(repo_id)
        if repo_f.exception():
            return repo_f

        units = self._repo_units.get(repo_id, set())
        out = []

        try:
            for unit in units:
                if match_object(criteria, unit):
                    out.append(unit)
        except Exception as ex:  # pylint: disable=broad-except
            return f_return_error(ex)

        random.shuffle(out)
        return self._prepare_pages(out)

    def _prepare_pages(self, resource_list):
        # Split resource_list into pages
        # resource_list: list of objects that paginated
        page_data = []
        current_page_data = []
        while resource_list:
            next_elem = resource_list.pop()
            current_page_data.append(next_elem)
            if len(current_page_data) == self._PAGE_SIZE and resource_list:
                page_data.append(current_page_data)
                current_page_data = []

        page_data.append(current_page_data)

        page = Page()
        next_page = None
        for batch in reversed(page_data):
            page = Page(data=batch, next=next_page)
            next_page = f_proxy(f_return(page))

        return f_proxy(f_return(page))

    def get_repository(self, repository_id):
        if not isinstance(repository_id, six.string_types):
            raise TypeError("Invalid argument: id=%s" % id)

        data = self.search_repository(Criteria.with_id(repository_id)).result().data
        if len(data) != 1:
            return f_return_error(
                PulpException("Repository id=%s not found" % repository_id)
            )

        return f_proxy(f_return(data[0]))

    def get_maintenance_report(self):
        self._ensure_alive()

        if self._maintenance_report:
            report = MaintenanceReport._from_data(json.loads(self._maintenance_report))
        else:
            report = MaintenanceReport()
        return f_proxy(f_return(report))

    def set_maintenance(self, report):
        self._ensure_alive()

        report_json = json.dumps(report._export_dict(), indent=4, sort_keys=True)
        report_fileobj = StringIO(report_json)

        repo = self.get_repository("redhat-maintenance").result()

        # upload updated report to repository and publish
        upload_ft = repo.upload_file(report_fileobj, "repos.json")

        publish_ft = f_flat_map(upload_ft, lambda _: repo.publish())
        self._maintenance_report = report_json

        return f_proxy(publish_ft)

    def get_content_type_ids(self):
        self._ensure_alive()

        return f_proxy(f_return(self._type_ids))

    def _do_upload_file(self, upload_id, file_obj, name):
        # pylint: disable=unused-argument
        is_file_obj = "close" in dir(file_obj)
        if not is_file_obj:
            file_obj = open(file_obj, "rb")

        def do_next_upload(checksum, size):
            data = file_obj.read(1024 * 1024)
            if data:
                if isinstance(data, six.text_type):
                    data = data.encode("utf-8")
                checksum.update(data)
                size += len(data)
                return do_next_upload(checksum, size)
            return f_return((checksum.hexdigest(), size))

        out = f_flat_map(f_return(), lambda _: do_next_upload(hashlib.sha256(), 0))

        if not is_file_obj:
            out.add_done_callback(lambda _: file_obj.close())

        return out

    def _do_unassociate(self, repo_id, criteria=None):
        repo_f = self.get_repository(repo_id)
        if repo_f.exception():
            return repo_f

        current = self._repo_units.get(repo_id, set())
        removed = set()
        kept = set()

        # use type hint=Unit so that if type_ids are the goal here
        # then we will get back a properly prepared PulpSearch with
        # a populated type_ids field
        pulp_search = search_for_criteria(criteria, type_hint=Unit, type_ids_accum=None)

        for unit in current:
            if (
                pulp_search.type_ids is None
                or unit.content_type_id in pulp_search.type_ids
            ):
                removed.add(unit)
            else:
                kept.add(unit)

        self._repo_units[repo_id] = kept

        task = Task(
            id=self._next_task_id(),
            repo_id=repo_id,
            completed=True,
            succeeded=True,
            units=removed,
        )

        return f_return([task])

    def _request_upload(self):
        upload_request = {
            "_href": "/pulp/api/v2/content/uploads/%s/" % self._next_request_id(),
            "upload_id": "%s" % self._next_request_id(),
        }

        return f_return(upload_request)

    def _do_import(self, repo_id, upload_id, unit_type_id, unit_key):
        # pylint: disable=unused-argument
        repo_f = self.get_repository(repo_id)
        if repo_f.exception():
            # Repo can't be found, let that exception propagate
            return repo_f

        repo = repo_f.result()

        task = Task(id=self._next_task_id(), completed=True, succeeded=True)

        self._upload_history.append(
            Upload(repo, [task], unit_key["name"], unit_key["checksum"])
        )

        return f_return([task])

    def _delete_resource(self, resource_type, resource_id):
        if resource_type == "repositories":
            return self._delete_repository(resource_id)

        match = re.match(r"^repositories/([^/]+)/distributors$", resource_type)
        if match:
            return self._delete_distributor(match.group(1), resource_id)

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
            self._repo_units.pop(repo_id, None)
            return f_return(
                [Task(id=self._next_task_id(), completed=True, succeeded=True)]
            )

    def _delete_distributor(self, repo_id, distributor_id):
        with self._lock:
            repo_f = self.get_repository(repo_id)
            if repo_f.exception():
                # Repo can't be found, let that exception propagate
                return repo_f

            repo = repo_f.result()
            new_distributors = [
                dist for dist in repo.distributors if dist.id != distributor_id
            ]
            dist_found = new_distributors != repo.distributors

            if not dist_found:
                # Deleting something which already doesn't exist is fine
                return f_return([])

            idx = self._repositories.index(repo)
            self._repositories[idx] = attr.evolve(repo, distributors=new_distributors)

            return f_return(
                [
                    Task(
                        id=self._next_task_id(),
                        completed=True,
                        succeeded=True,
                        tags=[
                            "pulp:repository:%s" % repo_id,
                            "pulp:repository_distributor:%s" % distributor_id,
                            "pulp:action:remove_distributor",
                        ],
                    )
                ]
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

    def _attach_repo(self, repo):
        kwargs = {}
        if repo.distributors:
            # Deep copy for accurate attach/detach semantics
            kwargs["distributors"] = [attr.evolve(dist) for dist in repo.distributors]

        repo = attr.evolve(repo, **kwargs)
        repo._set_client(self)
        return repo

    def _do_sync(self, repo_id, sync_config):  # pylint:disable = unused-argument
        repo_f = self.get_repository(repo_id)
        if repo_f.exception():
            # Repo can't be found, let that exception propagate
            return repo_f

        task = Task(id=self._next_task_id(), completed=True, succeeded=True)

        self._sync_history.append(Sync(repo_f.result(), [task], sync_config))

        return f_return([task])

    def _next_task_id(self):
        with self._lock:
            next_raw_id = self._uuidgen.randint(0, 2 ** 128)
        return str(uuid.UUID(int=next_raw_id))

    def _next_request_id(self):
        return self._next_task_id()
