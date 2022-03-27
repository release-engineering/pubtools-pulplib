import hashlib
import json
import logging
import os
import threading
from functools import partial
from collections import namedtuple

import requests
import six
from more_executors import Executors
from more_executors.futures import f_map, f_flat_map, f_return, f_proxy, f_sequence
from six.moves import StringIO

from ..page import Page
from ..criteria import Criteria
from ..model import (
    Repository,
    FileRepository,
    YumRepository,
    MaintenanceReport,
    Distributor,
    Unit,
    Task,
)
from ..log import TimedLogger
from ..util import dict_put
from .search import search_for_criteria
from .errors import PulpException
from .poller import TaskPoller
from . import retry
from .humanize_compat import naturalsize

from .ud_mappings import compile_ud_mappings
from .copy import CopyOptions


LOG = logging.getLogger("pubtools.pulplib")

UploadResult = namedtuple("UploadResult", ["checksum", "size"])


class Client(object):
    """A client for the Pulp 2.x API.

    This class provides high-level methods for querying a Pulp server and performing
    actions in Pulp.

    **Usage of futures:**

    Most values are returned as :class:`~concurrent.futures.Future` objects.
    Returned futures are resolved when:

    - a request to Pulp succeeded, if operation is synchronous (e.g. get, search)
    - or a request to Pulp succeeded and any spawned tasks succeeded, if operation
      is asynchronous (e.g. publish)

    If a future is currently awaiting one or more Pulp tasks, cancelling the future
    will attempt to cancel those tasks.

    **Client lifecycle:**

    .. versionadded:: 2.12.0

    Client instances support the context manager protocol and can be used
    via a ``with`` statement, as in example:

    .. code-block:: python

        with Client(url="https://pulp.example.com/") as client:
            do_something_with(client)

    While not mandatory, it is encouraged to ensure that any threads associated with
    the client are promptly shut down.

    **Proxy futures:**

    .. versionadded:: 2.1.0

    All :class:`~concurrent.futures.Future` objects produced by this client are
    *proxy futures*, meaning that attribute and method lookups on the objects are
    proxied to the future's result, blocking as needed.

    This allows the client to be used within blocking code without having to
    scatter calls to ``.result()`` throughout.

    For example, this block of code:

    .. code-block:: python

        repo = client.get_repository(repo_id).result()
        publish_tasks = repo.publish().result()
        task_ids = ','.join([t.id for t in publish_tasks])
        log.info("Published %s: %s", repo.id, task_ids)

    ...may be alternatively written without the calls to ``.result()``, due to
    the usage of proxy futures:

    .. code-block:: python

        repo = client.get_repository(repo_id)
        publish_tasks = repo.publish()
        task_ids = ','.join([t.id for t in publish_tasks])
        log.info("Published %s: %s", repo.id, task_ids)

    **Retries:**

    In general, for all methods which represent an idempotent operation and
    which return a Future, the library may retry operations several times in case
    of failure.

    **Throttling:**

    This client will internally throttle the number of Pulp tasks allowed to be
    outstanding at any given time, so that no single client can overload the Pulp
    task queue.
    """

    # Various defaults can be controlled by environment variables.
    # These are not a documented/supported feature of the library.
    # They're more of an emergency escape hatch to temporarily resolve issues.
    _REQUEST_THREADS = int(os.environ.get("PUBTOOLS_PULPLIB_REQUEST_THREADS", "4"))
    _UPLOAD_THREADS = int(os.environ.get("PUBTOOLS_PULPLIB_UPLOAD_THREADS", "4"))
    _PAGE_SIZE = int(os.environ.get("PUBTOOLS_PULPLIB_PAGE_SIZE", "2000"))
    _TASK_THROTTLE = int(os.environ.get("PUBTOOLS_PULPLIB_TASK_THROTTLE", "200"))
    _CHUNK_SIZE = int(os.environ.get("PUBTOOLS_PULPLIB_CHUNK_SIZE", 1024 * 1024 * 10))

    # Policy used when deciding whether to retry operations.
    # This is mainly provided here as a hook for autotests, so the policy can be
    # overridden there.
    _RETRY_POLICY = retry.PulpRetryPolicy()

    def __init__(self, url, **kwargs):
        """
        Args:
            str url
                URL of a Pulp server, e.g. https://pulp.example.com/.

            int task_throttle
                Maximum number of queued or running tasks permitted for this client.
                If more than this number of tasks are running, the client will wait before triggering more.
                This can be used to ensure no single client overwhelms the Pulp server.

            object auth, cert, headers, max_redirects, params, proxies, verify
                Any of these arguments, if provided, are used to initialize
                :class:`requests.Session` objects used by the client.

                These may be used, for example, to configure the credentials
                for the Pulp server or to use an alternative CA bundle.
        """
        self._url = url

        while self._url.endswith("/"):
            self._url = self._url[:-1]

        self._session_kwargs = {}
        for arg in (
            "auth",
            "cert",
            "headers",
            "max_redirects",
            "params",
            "proxies",
            "verify",
        ):
            if arg in kwargs:
                self._session_kwargs[arg] = kwargs.pop(arg)

        _task_throttle = kwargs.pop("task_throttle", self._TASK_THROTTLE)

        if kwargs:
            raise TypeError(
                "Unexpected keyword argument(s) %s" % ",".join(kwargs.keys())
            )

        self._tls = threading.local()

        # Cache supported types, used during searches.
        self._server_type_ids = None

        # executor only for issuing HTTP requests to Pulp:
        # - does not cover watching Pulp tasks
        # - checks HTTP response and raises if it's not JSON or
        #   it's not successful
        self._request_executor = (
            Executors.thread_pool(
                name="pubtools-pulplib-requests", max_workers=self._REQUEST_THREADS
            )
            .with_map(self._unpack_response)
            .with_retry(retry_policy=self._RETRY_POLICY)
        )

        # executor for uploads:
        # - reading of file content for upload, and calculation of checksums,
        #   happens in this executor
        # - HTTP requests don't happen here and are still submitted via
        #   request_executor (hence no retry needed on this executor)
        self._upload_executor = Executors.thread_pool(
            name="pubtools-pulplib-uploads", max_workers=self._UPLOAD_THREADS
        )

        # executor for issuing HTTP requests to Pulp which spawn tasks:
        # - checks HTTP response and raises if it's not JSON or
        #   it's not successful
        # - unpacks spawned_tasks from response to find task IDs to watch
        # - waits for tasks to complete
        # - retries whole thing (resubmitting request & making a new task) if needed
        # - throttles number of tasks pending
        poller = TaskPoller(self._new_session(), self._url)
        self._task_executor = (
            Executors.thread_pool(
                name="pubtools-pulplib-tasks", max_workers=self._REQUEST_THREADS
            )
            .with_map(self._unpack_response)
            .with_map(self._log_spawned_tasks)
            .with_poll(poller, cancel_fn=poller.cancel)
            .with_throttle(_task_throttle)
            .with_retry(retry_policy=self._RETRY_POLICY)
        )

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self._request_executor.__exit__(*args, **kwargs)
        self._upload_executor.__exit__(*args, **kwargs)
        self._task_executor.__exit__(*args, **kwargs)

    def get_repository(self, repository_id):
        """Get a repository by ID.

        Args:
            repository_id (str)
                The ID of the repository to be fetched.

        Returns:
            Future[:class:`~pubtools.pulplib.Repository`]
                A future holding the fetched Repository.
        """
        page_f = self.search_repository(Criteria.with_id(repository_id))

        def unpack_page(page):
            if len(page.data) != 1:
                raise PulpException("Repository id=%s was not found" % repository_id)
            return page.data[0]

        repo_f = f_map(page_f, unpack_page)
        return f_proxy(repo_f)

    def search_repository(self, criteria=None):
        """Search for repositories matching the given criteria.

        Args:
            criteria (:class:`~pubtools.pulplib.Criteria`)
                A criteria object used for this search.
                If None, search for all repositories.

        Returns:
            Future[:class:`~pubtools.pulplib.Page`]
                A future representing the first page of results.

                Each page will contain a collection of
                :class:`~pubtools.pulplib.Repository` objects.
        """
        search_options = {"distributors": True}
        return self._search(
            Repository, "repositories", criteria=criteria, search_options=search_options
        )

    def search_content(self, criteria=None):
        """Search for units across all repositories.

        Args:
            criteria (:class:`~pubtools.pulplib.Criteria`)
                A criteria object used for this search.
                If None, search for all units.

        Returns:
            Future[:class:`~pubtools.pulplib.Page`]
                A future representing the first page of results.

                Each page will contain a collection of
                :class:`~pubtools.pulplib.Unit` subclasses objects.

        .. versionadded:: 2.6.0
        """
        # Criteria will be serialized into a Pulp search at the time we
        # actually do the query, but validate eagerly as well so we raise
        # ASAP on invalid input.
        search_for_criteria(criteria, Unit, None)

        if self._server_type_ids is None:
            # We'll be using this in a moment either to set default IDs or to
            # reject searches for invalid types.
            # Note: no locking, so if we're called from multiple threads we in
            # theory might waste some time querying the types more than once.
            self._server_type_ids = self.get_content_type_ids()

        return f_proxy(
            f_flat_map(
                self._server_type_ids,
                lambda ids: self._search_content_with_server_type_ids(criteria, ids),
            )
        )

    def copy_content(
        self, from_repository, to_repository, criteria=None, options=CopyOptions()
    ):
        """Copy content from one repository to another.

        Args:
            from_repository (:class:`~pubtools.pulplib.Repository`)
                A repository used as the source of content.

            to_repository (:class:`~pubtools.pulplib.Repository`)
                A repository to receive copied content.

            criteria (:class:`~pubtools.pulplib.Criteria`)
                A criteria object used to find units for copy.
                If None, all units in the source repo will be copied.

            options (:class:`~pubtools.pulplib.CopyOptions`)
                Options influencing the copy.

                Some options may be specific to certain repository and content
                types. Options which are not applicable to this copy will be
                ignored.

        Returns:
            Future[list[:class:`~pubtools.pulplib.Task`]]
                A future which is resolved when the copy completes.

                The :meth:`~pubtools.pulplib.Task.units` attribute may be inspected
                to determine which unit(s) were copied. Note that the returned units
                typically will have only a subset of available fields.

        .. versionadded:: 2.17.0

        .. versionadded:: 2.29.0
            Added the ``options`` argument.
        """

        raw_options = {}

        if (
            isinstance(to_repository, YumRepository)
            and options.require_signed_rpms is not None
        ):
            dict_put(
                raw_options,
                "override_config.require_signature",
                options.require_signed_rpms,
            )

        return f_proxy(
            self._do_associate(
                from_repository.id, to_repository.id, criteria, raw_options
            )
        )

    def update_content(self, unit):
        """Update mutable fields on an existing unit.

        Args:
            unit (:class:`~pubtools.pulplib.Unit`)
                A unit to be updated.

                This unit must have a known ``unit_id``.

                Only those fields documented as *mutable* will have any effect during
                the update (e.g. ``cdn_path``). Other fields either cannot be updated
                at all, or can only be updated by re-uploading the associated content.

        Returns:
            Future
                A future which is resolved with a value of ``None`` once the unit
                has been updated.

        .. versionadded:: 2.20.0
        """

        if not unit.unit_id:
            raise ValueError("unit_id missing on call to update_content()")

        url = os.path.join(
            self._url,
            "pulp/api/v2/content/units/%s/%s/pulp_user_metadata/"
            % (unit.content_type_id, unit.unit_id),
        )

        out = self._request_executor.submit(
            self._do_request, method="PUT", url=url, json=unit._usermeta
        )

        # The Pulp API is defined as returning 'null' so this should be a no-op,
        # but to be extra sure we don't return anything unexpected, we'll force
        # the return value to None.
        out = f_map(out, lambda _: None)

        return out

    def update_repository(self, repository):
        """Update mutable fields on an existing repository.

        Args:
            repository (:class:`~pubtools.pulplib.Repository`)
                A repository to be updated.

                Only those fields documented as *mutable* will have any effect during
                the update (e.g. ``product_versions``). Other fields cannot be updated
                using this library.

        Returns:
            Future
                A future which is resolved with a value of ``None`` once the
                repository has been updated.

        .. versionadded:: 2.29.0
        """

        url = os.path.join(self._url, "pulp/api/v2/repositories/%s/" % repository.id)

        update = {"delta": {"notes": repository._mutable_notes}}
        out = self._request_executor.submit(
            self._do_request, method="PUT", url=url, json=update
        )

        # The Pulp API may actually return an updated version of the repository,
        # but for consistency with update_content we won't return it.
        # The caller can re-fetch if desired.
        out = f_map(out, lambda _: None)

        return out

    def _search_content_with_server_type_ids(self, criteria, server_type_ids):
        prepared_search = search_for_criteria(criteria, Unit, None)
        type_ids = prepared_search.type_ids
        if not type_ids:
            type_ids = server_type_ids
        missing = set(type_ids) - set(server_type_ids)
        if missing:
            raise ValueError(
                "Content type: %s is not supported by server" % ",".join(missing)
            )

        return self._search(
            Unit,
            ["content/units/%s" % x for x in type_ids],
            criteria=criteria,
            search_options={"include_repos": True},
        )

    def search_distributor(self, criteria=None):
        """Search the distributors matching the given criteria.

        Args:
            criteria (:class:`~pubtools.pulplib.Criteria`)
                A criteria object used for this search.
                If None, search for all distributors.

        Returns:
            Future[:class:`~pubtools.pulplib.Page`]
                A future representing the first page of results.

                Each page will contain a collection of
                :class:`~pubtools.pulplib.Distributor` objects.

        .. versionadded:: 2.1.0
        """
        return self._search(Distributor, "distributors", criteria=criteria)

    def search_task(self, criteria=None):
        """Search the tasks matching the given criteria.

        Args:
            criteria (:class:`~pubtools.pulplib.Criteria`)
                A criteria object used for this search.
                If None, search for all tasks.

        Returns:
            Future[:class:`~pubtools.pulplib.Page`]
                A future representing the first page of results.

                Each page will contain a collection of
                :class:`~pubtools.pulplib.Task` objects.

        .. versionadded:: 2.19.0
        """
        return self._search(Task, "tasks", criteria=criteria)

    def _search(
        self,
        return_type,
        resource_types,
        search_type="search",
        search_options=None,
        criteria=None,
    ):  # pylint:disable = too-many-arguments

        if not isinstance(resource_types, (list, tuple)):
            resource_types = [resource_types]

        responses = []
        searches = []
        urls = []
        for resource_type in resource_types:
            url = os.path.join(
                self._url, "pulp/api/v2/%s/%s/" % (resource_type, search_type)
            )
            urls.append(url)
            prepared_search = search_for_criteria(criteria, return_type)

            search = {
                "criteria": {
                    "skip": 0,
                    "limit": self._PAGE_SIZE,
                    "filters": prepared_search.filters,
                }
            }
            search.update(search_options or {})

            if search_type == "search/units":
                # Unit searches need a little special handling:
                # - serialization might have extracted some type_ids
                # - filters should be wrapped under 'unit'
                #   (we do not support searching on associations right now)
                if prepared_search.type_ids:
                    search["criteria"]["type_ids"] = prepared_search.type_ids
                search["criteria"]["filters"] = {"unit": search["criteria"]["filters"]}

            searches.append(search)
            responses.append(self._do_search(url, search))

        # When this request is resolved, we'll have the first page of data.
        # We'll need to convert that into a page and also keep going with
        # the search if there's more to be done.
        return f_proxy(
            f_map(
                f_sequence(responses),
                lambda data: self._handle_page(urls, return_type, searches, data),
            )
        )

    def _search_repo_units(self, repo_id, criteria):
        resource_type = "repositories/%s" % repo_id

        return self._search(
            Unit, resource_type, search_type="search/units", criteria=criteria
        )

    def get_maintenance_report(self):
        """Get the current maintenance mode status for this Pulp server.

        Returns:
            Future[:class:`~pubtools.pulplib.MaintenanceReport`]
                A future describes the maintenance status

        .. versionadded:: 1.4.0
        """
        report_ft = self._do_get_maintenance()

        return f_map(
            report_ft,
            lambda data: MaintenanceReport._from_data(data)
            if data
            else MaintenanceReport(),
        )

    def set_maintenance(self, report):
        """Set maintenance mode for this Pulp server.

        Args:
            report:
                An updated :class:`~pubtools.pulplib.MaintenanceReport` object that
                will be used as the newest maintenance report.
        Return:
            Future[list[:class:`~pubtools.pulplib.Task`]]
                A future which is resolved when maintenance mode has been updated successfully.

                The future contains a task triggered and awaited during the publish
                maintenance repository operation.

        .. versionadded:: 1.4.0
        """
        report_json = json.dumps(report._export_dict(), indent=4, sort_keys=True)
        report_fileobj = StringIO(report_json)

        repo = self.get_repository("redhat-maintenance").result()

        # upload updated report to repository and publish
        upload_ft = repo.upload_file(report_fileobj, "repos.json")

        return f_flat_map(upload_ft, lambda _: repo.publish())

    def get_content_type_ids(self):
        """Get the content types supported by this Pulp server.

        Returns:
            Future[list[str]]
                A future holding the IDs of supported content types.

                The returned values will depend on the plugins installed
                on the connected Pulp server.

                "modulemd", "rpm", "srpm" and "erratum" are some examples
                of common return values.

        .. versionadded:: 1.4.0
        """
        url = os.path.join(self._url, "pulp/api/v2/plugins/types/")

        out = self._request_executor.submit(self._do_request, method="GET", url=url)

        # The pulp API returns an object per supported type.
        # We only support returning the ID at this time.
        return f_proxy(f_map(out, lambda types: sorted([t["id"] for t in types])))

    def _do_upload_file(self, upload_id, file_obj, name="<unknown file>"):
        return self._upload_executor.submit(
            self._upload_file_loop, upload_id, file_obj, name
        )

    def _upload_file_loop(self, upload_id, file_obj, name):
        # Read a file in chunks, upload it to pulp under the given upload_id,
        # and return the checksum & bytes read.
        #
        # This method will block for the entire duration of the upload, which can
        # be slow for a large file. It is intended to be invoked only from within
        # the upload_executor in order to avoid blocking other operations.

        total_size = None

        is_file_object = "close" in dir(file_obj)
        if not is_file_object:
            # This is the preferred case (we're responsible for opening the file),
            # as we can then know the total expected size. (file-like objects in
            # general do not know their own size)
            total_size = os.path.getsize(file_obj)
            file_obj = open(file_obj, "rb")

        upload_logger = TimedLogger()
        checksum = hashlib.sha256()
        size = 0

        # We allow having a few chunks in flight at once, up to as many requests
        # as we can do in parallel.
        prev_chunks = [f_return() for _ in range(0, self._REQUEST_THREADS)]

        try:
            while True:
                data = file_obj.read(self._CHUNK_SIZE)

                if not data:
                    break

                if isinstance(data, six.text_type):
                    # if it's unicode, need to encode before calculate checksum
                    data = data.encode("utf-8")

                checksum.update(data)

                # Ensure the number of chunks are kept at a fixed size by waiting
                # for one of them to complete.
                prev_chunks.pop(0).result()

                # Then start upload of this chunk to Pulp.
                prev_chunks.append(self._do_upload(data, upload_id, size))

                size += len(data)

                # Log a message about the upload progress.
                if not total_size:
                    # no percentage can be calculated
                    pct = ""
                else:
                    pct = float(size) / total_size * 100
                    pct = " / %2d%%" % pct

                upload_logger.info(
                    "Still uploading %s: %s%s [%s]",
                    name,
                    naturalsize(size),
                    pct,
                    upload_id,
                )

            # No more data to read. As soon as all chunks in progress are done,
            # we have finished with the upload.
            for chunk in prev_chunks:
                chunk.result()

            return UploadResult(checksum.hexdigest(), size)

        finally:
            file_obj.close()

    def _publish_repository(self, repo, distributors_with_config):
        compiled = self._compile_notes(repo)

        tasks_f = f_map(compiled, lambda _: [])

        def do_next_publish(accumulated_tasks, distributor, config):
            distributor_tasks_f = self._publish_distributor(
                repo.id, distributor.id, config
            )
            return f_map(
                distributor_tasks_f,
                lambda distributor_tasks: accumulated_tasks + distributor_tasks,
            )

        for (distributor, config) in distributors_with_config:
            next_publish = partial(
                do_next_publish, distributor=distributor, config=config
            )
            tasks_f = f_flat_map(tasks_f, next_publish)

        return tasks_f

    def _publish_distributor(self, repo_id, distributor_id, override_config):
        url = os.path.join(
            self._url, "pulp/api/v2/repositories/%s/actions/publish/" % repo_id
        )
        body = {"id": distributor_id, "override_config": override_config}
        return self._task_executor.submit(
            self._do_request, method="POST", url=url, json=body
        )

    def _do_associate(self, src_repo_id, dest_repo_id, criteria=None, raw_options=None):
        url = os.path.join(
            self._url, "pulp/api/v2/repositories/%s/actions/associate/" % dest_repo_id
        )

        pulp_search = search_for_criteria(criteria, type_hint=Unit, type_ids_accum=None)

        body = {"source_repo_id": src_repo_id, "criteria": {}}
        if pulp_search.type_ids:
            body["criteria"]["type_ids"] = pulp_search.type_ids
        if pulp_search.filters:
            body["criteria"]["filters"] = {"unit": pulp_search.filters}

        body.update(raw_options or {})

        LOG.debug("Submitting %s associate: %s", url, body)

        return self._task_executor.submit(
            self._do_request, method="POST", url=url, json=body
        )

    def _do_unassociate(self, repo_id, criteria=None):
        url = os.path.join(
            self._url, "pulp/api/v2/repositories/%s/actions/unassociate/" % repo_id
        )

        # use type hint=Unit so that if type_ids are the goal here
        # then we will get back a properly prepared PulpSearch with
        # a populated type_ids field
        pulp_search = search_for_criteria(criteria, type_hint=Unit, type_ids_accum=None)

        body = {"criteria": {"type_ids": pulp_search.type_ids}}

        if pulp_search.filters:
            # Filters to remove content are only effective when provided
            # with a type_id. Otherwise filters are skipped and all the
            # content is removed.
            if not pulp_search.type_ids:
                raise ValueError(
                    "Criteria to remove_content must specify at least one unit type!"
                )
            else:
                body["criteria"]["filters"] = {"unit": pulp_search.filters}

        LOG.debug("Submitting %s unassociate: %s", url, body)

        return self._task_executor.submit(
            self._do_request, method="POST", url=url, json=body
        )

    def _compile_notes(self, repo):
        # Given a repo we're about to publish, calculate and set certain notes
        # derived from the repo contents.
        out = f_return()

        if isinstance(repo, FileRepository):
            out = compile_ud_mappings(
                repo,
                # UD mapping code is written to do low-level pulp requests.
                # In order to keep the code at arms length and don't let it access
                # client internals directly, we'll just pass a callback
                # it can use to do these requests.
                do_request=lambda url, **kwargs: self._request_executor.submit(
                    self._do_request, url=os.path.join(self._url, url), **kwargs
                ),
            )

        return out

    @classmethod
    def _unpack_response(cls, pulp_response):
        try:
            parsed = pulp_response.json()
        except Exception:
            # Couldn't parse as JSON?
            # If the response was unsuccessful, raise that.
            # Otherwise re-raise parse error.
            pulp_response.raise_for_status()
            raise

        if (
            isinstance(parsed, dict)
            and parsed.get("http_status") == 404
            and parsed.get("http_request_method") == "DELETE"
        ):
            # Special case allowing unsuccessful status:
            # If we asked to DELETE something, and we got a 404 response,
            # this is not considered an error because the postcondition
            # of our request is satisfied.
            # Hence, don't call raise_for_status.
            pass
        else:
            # In general, we'll raise if response was unsuccessful.
            pulp_response.raise_for_status()

        return parsed

    @classmethod
    def _log_spawned_tasks(cls, taskdata):
        try:
            spawned = taskdata.get("spawned_tasks") or []
            for task in spawned:
                LOG.info("Created Pulp task: %s", task["task_id"])
        except Exception:  # pylint: disable=broad-except
            # something wrong with the data, can't log.
            # This error will be raised elsewhere
            pass
        return taskdata

    def _handle_page(self, urls, object_class, searches, raw_data_list):

        page_data = []
        for url, search, raw_data in zip(urls, searches, raw_data_list):
            # Extract metadata from Pulp units
            LOG.debug("Got pulp response for %s, %s elems", search, len(raw_data))
            if object_class is Unit and url.endswith("units/"):
                raw_data = [elem["metadata"] for elem in raw_data]

            page_data.extend([object_class.from_data(elem) for elem in raw_data])

        for obj in page_data:
            # set_client is only applicable for repository and distributor objects
            if hasattr(obj, "_set_client"):
                obj._set_client(self)

        # Do we need a next page?
        next_page = None

        next_responses = []
        next_searches = []
        next_urls = []
        for url, search, raw_data in zip(urls, searches, raw_data_list):
            limit = search["criteria"]["limit"]
            if len(raw_data) == limit:
                # Yeah, we might...
                search = search.copy()
                search["criteria"] = search["criteria"].copy()
                search["criteria"]["skip"] = search["criteria"]["skip"] + limit
                response_f = self._do_search(url, search)
                next_searches.append(search)
                next_responses.append(response_f)
                next_urls.append(url)

        if next_responses:
            next_page = f_proxy(
                f_map(
                    f_sequence(next_responses),
                    lambda data: self._handle_page(
                        next_urls, object_class, next_searches, data
                    ),
                )
            )
        return Page(data=page_data, next=next_page)

    @property
    def _session(self):
        if not hasattr(self._tls, "session"):
            self._tls.session = self._new_session()
        return self._tls.session

    def _new_session(self):
        out = requests.Session()
        for key, value in self._session_kwargs.items():
            setattr(out, key, value)
        return out

    def _do_request(self, **kwargs):
        return self._session.request(**kwargs)

    def _do_search(self, url, search):
        LOG.debug("Submitting %s search: %s", url, search)
        return self._request_executor.submit(
            self._do_request, method="POST", url=url, json=search
        )

    def _delete_resource(self, resource_type, resource_id):
        url = os.path.join(
            self._url, "pulp/api/v2/%s/%s/" % (resource_type, resource_id)
        )

        LOG.debug("Queuing request to DELETE %s", url)
        return self._task_executor.submit(self._do_request, method="DELETE", url=url)

    def _request_upload(self, name):
        url = os.path.join(self._url, "pulp/api/v2/content/uploads/")

        LOG.debug("Requesting upload id for %s", name)
        return self._request_executor.submit(self._do_request, method="POST", url=url)

    def _do_upload(self, data, upload_id, offset):
        url = os.path.join(
            self._url, "pulp/api/v2/content/uploads/%s/%s/" % (upload_id, offset)
        )

        return self._request_executor.submit(
            self._do_request, method="PUT", url=url, data=data
        )

    def _do_import(
        self, repo_id, upload_id, unit_type_id, unit_key, unit_metadata=None
    ):
        url = os.path.join(
            self._url, "pulp/api/v2/repositories/%s/actions/import_upload/" % repo_id
        )

        unit_metadata = unit_metadata or {}

        body = {
            "unit_type_id": unit_type_id,
            "upload_id": upload_id,
            "unit_key": unit_key,
            "unit_metadata": unit_metadata,
        }

        LOG.debug("Importing contents to repo %s with upload id %s", repo_id, upload_id)
        return self._task_executor.submit(
            self._do_request, method="POST", url=url, json=body
        )

    def _delete_upload_request(self, upload_id, name):
        url = os.path.join(self._url, "pulp/api/v2/content/uploads/%s/" % upload_id)

        LOG.debug("Deleting upload request %s for %s", upload_id, name)
        return self._request_executor.submit(self._do_request, method="DELETE", url=url)

    def _do_get_maintenance(self):
        def map_404_to_none(exception):
            # Translates 404 errors to a None response (no maintenance report).
            if (
                getattr(exception, "response", None) is not None
                and exception.response.status_code == 404
            ):
                return None
            # Any other types of errors are raised unchanged.
            raise exception

        url = os.path.join(self._url, "pulp/isos/redhat-maintenance/repos.json")

        response = self._request_executor.submit(
            self._do_request, method="GET", url=url
        )

        return f_map(response, error_fn=map_404_to_none)

    def _do_sync(self, repo_id, sync_options):
        if not sync_options["feed"]:
            raise ValueError("Cannot sync with empty feed: '%s'" % sync_options["feed"])

        url = os.path.join(
            self._url, "pulp/api/v2/repositories/%s/actions/sync/" % repo_id
        )

        body = {"override_config": sync_options}

        LOG.debug("Syncing repository %s with feed %s", repo_id, sync_options["feed"])
        return self._task_executor.submit(
            self._do_request, method="POST", url=url, json=body
        )
