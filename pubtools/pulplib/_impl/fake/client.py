import random
import hashlib
import json
import re

from collections import namedtuple

from io import StringIO, BytesIO

from more_executors.futures import f_return, f_return_error, f_flat_map, f_proxy

from pubtools.pulplib import (
    Page,
    PulpException,
    Criteria,
    Task,
    Repository,
    Distributor,
    Unit,
    RpmUnit,
    MaintenanceReport,
    CopyOptions,
)
from pubtools.pulplib._impl.client.client import UploadResult
from pubtools.pulplib._impl.client.search import search_for_criteria
from .. import compat_attr as attr

from .match import match_object
from . import units

Publish = namedtuple("Publish", ["repository", "tasks"])
Upload = namedtuple("Upload", ["repository", "tasks", "name", "sha256"])
Sync = namedtuple("Sync", ["repository", "tasks", "sync_config"])
RepoLockRecord = namedtuple("RepoLockRecord", ["repository", "action"])


class FakeClient(object):  # pylint:disable = too-many-instance-attributes
    # Client implementation holding data in memory rather than
    # using a remote Pulp server.
    #
    # This class is not public, but it must have all of the same public
    # API as the pubtools.pulplib.Client class. The idea is that any code
    # written against pubtools.pulplib.Client should be able to work with
    # an instance of this class swapped in.
    _PAGE_SIZE = 3

    def __init__(self, state):
        self._state = state
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
            for repo in self._state.repositories[:]:
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

        available_type_ids = set(self._state.type_ids)
        missing_type_ids = set(prepared_search.type_ids or []) - available_type_ids
        if missing_type_ids:
            return f_return_error(
                PulpException(
                    "following type ids are not supported on the server: %s"
                    % ",".join(missing_type_ids)
                )
            )

        for unit in self._state.all_units:
            if (
                prepared_search.type_ids
                and unit.content_type_id not in prepared_search.type_ids
            ):
                continue
            if match_object(criteria, unit):
                unit = units.with_filtered_fields(unit, prepared_search.unit_fields)
                out.append(unit)

        # callers should not make any assumption about the order of returned
        # values. Encourage that by returning output in unpredictable order
        random.shuffle(out)
        return self._prepare_pages(out)

    def copy_content(
        self, from_repository, to_repository, criteria=None, options=CopyOptions()
    ):
        self._ensure_alive()

        from_id = from_repository.id
        to_id = to_repository.id

        found = list(from_repository.search_content(criteria).result())

        # RPM signature filter: if signatures are required, unsigned RPMs are not
        # included in the copy.
        # Because we don't model this flag on distributor objects and because in
        # practice it's set to True, we default to True.
        if options.require_signed_rpms is not False:
            found = [u for u in found if not isinstance(u, RpmUnit) or u.signing_key]

        # Units are being copied to this repo, so that value obviously must appear
        # in repository_memberships from now on.
        found = [attr.evolve(unit, repository_memberships=[to_id]) for unit in found]

        with self._state.lock:
            # Now put the found units into the destination repo.
            # Any kind of merging or replacing of units is handled within this step.
            self._state.insert_repo_units(to_id, found)

            # Arbitrarily limit the number of units included per task. The point is
            # to enforce that the caller doesn't expect any specific number of tasks.
            tasks = []
            while found:
                next_batch = found[:5]
                found = found[5:]
                tasks.append(
                    Task(
                        id=self._state.next_task_id(),
                        repo_id=from_id,
                        completed=True,
                        succeeded=True,
                        units=units.with_key_only(next_batch),
                    )
                )

            if not tasks:
                # This indicates that nothing was found at all.
                # That's fine, just return a task with empty units.
                tasks.append(
                    Task(
                        id=self._state.next_task_id(),
                        repo_id=from_id,
                        completed=True,
                        succeeded=True,
                        units=[],
                    )
                )

        return f_proxy(f_return(tasks))

    def update_content(self, unit):
        self._ensure_alive()

        if not unit.unit_id:
            raise ValueError("unit_id missing on call to update_content()")

        with self._state.lock:
            # The unit has to exist.
            existing_unit = None
            for candidate in self._state.all_units:
                if (
                    candidate.content_type_id == unit.content_type_id
                    and candidate.unit_id == unit.unit_id
                ):
                    existing_unit = candidate
                    break
            else:
                return f_return_error(
                    PulpException("unit not found: %s" % unit.unit_id)
                )

            # OK, we have a unit to update. Figure out which fields we can update.
            update = {}
            for fld in unit._usermeta_fields():
                update[fld.name] = getattr(unit, fld.name)

            updated_unit = attr.evolve(existing_unit, **update)

            unit_key = units.make_unit_key(updated_unit)
            self._state.units_by_key[unit_key] = updated_unit

        return f_return()

    def update_repository(self, repository):
        self._ensure_alive()

        with self._state.lock:
            existing_repo = None
            for candidate in self._state.repositories:
                if candidate.id == repository.id:
                    existing_repo = candidate
                    break
            else:
                return f_return_error(
                    PulpException("repository not found: %s" % repository.id)
                )

            # We've got a repo, now update it.
            update = {}
            for fld in existing_repo._mutable_note_fields():
                update[fld.name] = getattr(repository, fld.name)

            updated_repo = attr.evolve(existing_repo, **update)

            self._state.repositories = [
                repo for repo in self._state.repositories if repo.id != updated_repo.id
            ] + [updated_repo]

        return f_return()

    def search_distributor(self, criteria=None):
        self._ensure_alive()

        criteria = criteria or Criteria.true()
        distributors = []

        search_for_criteria(criteria, Distributor)

        try:
            for repo in self._state.repositories[:]:
                for distributor in repo.distributors:
                    if match_object(criteria, distributor):
                        distributors.append(attr.evolve(distributor, repo_id=repo.id))
        except Exception as ex:  # pylint: disable=broad-except
            return f_return_error(ex)

        random.shuffle(distributors)
        return self._prepare_pages(distributors)

    def search_task(self, criteria=None):
        self._ensure_alive()
        tasks = []

        criteria = criteria or Criteria.true()
        search_for_criteria(criteria)

        try:
            for task in self._state.tasks[:]:
                if match_object(criteria, task):
                    tasks.append(task)
        except Exception as ex:  # pylint: disable=broad-except
            return f_return_error(ex)

        random.shuffle(tasks)
        return self._prepare_pages(tasks)

    def _search_repo_units(self, repo_id, criteria):
        criteria = criteria or Criteria.true()

        # Pass the criteria through the same handling as used by the real client
        # for serialization, to ensure we reject criteria also rejected by real client
        # and also accumulate unit_fields.
        prepared_search = search_for_criteria(criteria, Unit)

        repo_f = self.get_repository(repo_id)
        if repo_f.exception():
            return repo_f

        with self._state.lock:
            repo_units = self._state.repo_units(repo_id)

        out = []

        try:
            for unit in repo_units:
                if match_object(criteria, unit):
                    unit = units.with_filtered_fields(unit, prepared_search.unit_fields)
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
        if not isinstance(repository_id, str):
            raise TypeError("Invalid argument: id=%s" % id)

        data = self.search_repository(Criteria.with_id(repository_id)).result().data
        if len(data) != 1:
            return f_return_error(
                PulpException("Repository id=%s not found" % repository_id)
            )

        return f_proxy(f_return(data[0]))

    def get_maintenance_report(self):
        self._ensure_alive()

        with self._state.lock:
            if self._state.maintenance_report:
                report = MaintenanceReport._from_data(
                    json.loads(self._state.maintenance_report)
                )
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
        self._state.maintenance_report = report_json

        return f_proxy(publish_ft)

    def get_content_type_ids(self):
        self._ensure_alive()

        return f_proxy(f_return(self._state.type_ids))

    def _do_upload_file(
        self, upload_id, file_obj, name="<unknown file>"
    ):  # pylint: disable=unused-argument
        # We keep track of uploaded content as we may need it at import time.
        buffer = BytesIO()

        with self._state.lock:
            self._state.uploads_pending[upload_id] = buffer

        is_file_obj = "close" in dir(file_obj)
        if not is_file_obj:
            file_obj = open(file_obj, "rb")

        def do_next_upload(checksum, size):
            while True:
                data = file_obj.read(1024 * 1024)
                if not data:
                    break
                if isinstance(data, str):
                    data = data.encode("utf-8")
                buffer.write(data)
                checksum.update(data)
                size += len(data)

            return f_return(UploadResult(checksum.hexdigest(), size))

        out = f_flat_map(f_return(), lambda _: do_next_upload(hashlib.sha256(), 0))

        out.add_done_callback(lambda _: file_obj.close())

        return out

    def _do_unassociate(self, repo_id, criteria=None, limit=None):
        repo_f = self.get_repository(repo_id)
        if repo_f.exception():
            return repo_f

        with self._state.lock:
            current = self._state.repo_unit_keys.get(repo_id, set())
            units_with_key = [
                {"key": key, "unit": self._state.units_by_key[key]} for key in current
            ]
            removed_units = set()
            kept_keys = set()

            criteria = criteria or Criteria.true()
            # validating the criteria here like in actual scenario.
            pulp_search = search_for_criteria(
                criteria, type_hint=Unit, unit_type_accum=None
            )

            # raise an error if criteria with filters doesn't include type_ids
            if pulp_search.filters and not pulp_search.type_ids:
                raise ValueError(
                    "Criteria to remove_content must specify at least one unit type!"
                )

            for unit_with_key in units_with_key:
                unit = unit_with_key["unit"]
                if match_object(criteria, unit) and (
                    not limit or len(removed_units) < limit
                ):
                    removed_units.add(unit)
                else:
                    kept_keys.add(unit_with_key["key"])

            self._state.repo_unit_keys[repo_id] = kept_keys

            task = Task(
                id=self._state.next_task_id(),
                repo_id=repo_id,
                completed=True,
                succeeded=True,
                units=units.with_key_only(removed_units),
            )

        return f_return([task])

    def _get_repo_lock_data(self, repo_id):
        self._ensure_alive()
        data = self.search_repository(Criteria.with_id(repo_id)).result().data
        if len(data) != 1:
            return f_return_error(PulpException("Repository id=%s not found" % repo_id))
        with self._state.lock:
            data = (
                self._state.repo_locks[repo_id]
                if repo_id in self._state.repo_locks
                else {}
            )
            return f_return(data)

    # pylint: disable=unused-argument
    def _update_repo_lock_data(self, repo_id, note_delta, await_result=None):
        self._ensure_alive()
        data = self.search_repository(Criteria.with_id(repo_id)).result().data
        if len(data) != 1:
            return f_return_error(PulpException("Repository id=%s not found" % repo_id))
        with self._state.lock:

            data = (
                self._state.repo_locks[repo_id]
                if repo_id in self._state.repo_locks
                else {}
            )
            for lock_id in note_delta:
                data[lock_id] = note_delta[lock_id]

            data = {k: data[k] for k in data if data[k] is not None}
            self._state.repo_locks[repo_id] = data

            if len(note_delta) == 1:
                lock_id = list(note_delta)[0]
                self._state.repo_lock_history.append(
                    RepoLockRecord(repo_id, "lock" if note_delta[lock_id] else "unlock")
                )
            else:
                # The only time more than one change should be made is when
                # removing multiple expired locks.
                self._state.repo_lock_history.append(
                    RepoLockRecord(repo_id, "multi-unlock")
                )

    def _request_upload(self, name):  # pylint: disable=unused-argument
        # Note: old versions had a bug where this function would always
        # consume *two* request IDs. We keep that side-effect so that test
        # data produced with that bug remains stable.
        self._state.next_request_id()

        upload_id = self._state.next_request_id()
        upload_request = {
            "_href": "/pulp/api/v2/content/uploads/%s/" % upload_id,
            "upload_id": "%s" % upload_id,
        }

        return f_return(upload_request)

    def _do_import(
        self, repo_id, upload_id, unit_type_id, unit_key, unit_metadata=None
    ):
        repo_f = self.get_repository(repo_id)
        if repo_f.exception():
            # Repo can't be found, let that exception propagate
            return repo_f

        repo = repo_f.result()

        with self._state.lock:
            # Get the uploaded content we're about to import; though it's not
            # guaranteed to be present (e.g. erratum has no file).
            # If not present, we just use an empty BytesIO.
            upload_content = self._state.uploads_pending.pop(upload_id, BytesIO())
            upload_content.seek(0)

            new_units = self._state.unitmaker.make_units(
                unit_type_id, unit_key, unit_metadata, upload_content, repo_id
            )
            new_units = [
                attr.evolve(u, repository_memberships=[repo.id]) for u in new_units
            ]

            self._state.insert_repo_units(repo_id, new_units)

            task = Task(id=self._state.next_task_id(), completed=True, succeeded=True)

            # upload_history is a deprecated field, data is maintained for iso only.
            if unit_type_id == "iso":
                self._state.upload_history.append(
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
        with self._state.lock:
            found = False
            for idx, repo in enumerate(self._state.repositories):
                if repo.id == repo_id:
                    found = True
                    break

            if not found:
                # Deleting something which already doesn't exist is fine
                return f_return([])

            self._state.repositories.pop(idx)  # pylint: disable=undefined-loop-variable
            self._state.repo_unit_keys.pop(repo_id, None)
            return f_return(
                [Task(id=self._state.next_task_id(), completed=True, succeeded=True)]
            )

    def _delete_distributor(self, repo_id, distributor_id):
        with self._state.lock:
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

            idx = self._state.repositories.index(repo)
            self._state.repositories[idx] = attr.evolve(
                repo, distributors=new_distributors
            )

            return f_return(
                [
                    Task(
                        id=self._state.next_task_id(),
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

        with self._state.lock:
            tasks = []
            for _ in distributors_with_config:
                tasks.append(
                    Task(id=self._state.next_task_id(), completed=True, succeeded=True)
                )

            self._state.publish_history.append(Publish(repo, tasks))

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

        with self._state.lock:
            task = Task(id=self._state.next_task_id(), completed=True, succeeded=True)

            self._state.sync_history.append(Sync(repo_f.result(), [task], sync_config))

        return f_return([task])

    def create_repository(self, repo):
        with self._state.lock:
            if repo.id not in [
                existing_repo.id for existing_repo in self._state.repositories
            ]:
                self._state.repositories.append(repo)

        return self.get_repository(repo.id)
