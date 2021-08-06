import hashlib
import json
import logging
import os
import threading
from functools import partial

import requests
import six
from more_executors import Executors
from more_executors.futures import f_map, f_flat_map, f_return, f_proxy, f_sequence
from six.moves import StringIO

from ..page import Page
from ..criteria import Criteria
from ..model import Repository, MaintenanceReport, Distributor, Unit
from .search import search_for_criteria
from .errors import PulpException
from .poller import TaskPoller
from . import retry


LOG = logging.getLogger("pubtools.pulplib")


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
    _PAGE_SIZE = int(os.environ.get("PUBTOOLS_PULPLIB_PAGE_SIZE", "2000"))
    _TASK_THROTTLE = int(os.environ.get("PUBTOOLS_PULPLIB_TASK_THROTTLE", "200"))
    _CHUNK_SIZE = int(os.environ.get("PUBTOOLS_PULPLIB_CHUNK_SIZE", 1024 * 1024))

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

        server_type_ids = self.get_content_type_ids()
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
            Unit, ["content/units/%s" % x for x in type_ids], criteria=criteria
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

    def _do_upload_file(self, upload_id, file_obj, name):
        def do_next_upload(checksum, size):
            data = file_obj.read(self._CHUNK_SIZE)
            if data:
                if isinstance(data, six.text_type):
                    # if it's unicode, need to encode before calculate checksum
                    data = data.encode("utf-8")
                checksum.update(data)
                return f_flat_map(
                    self._do_upload(data, upload_id, size),
                    lambda _: do_next_upload(checksum, size + len(data)),
                )
            # nothing more to upload, return checksum and size
            return f_return((checksum.hexdigest(), size))

        is_file_object = "close" in dir(file_obj)
        if not is_file_object:
            file_obj = open(file_obj, "rb")

        LOG.info("Uploading %s to Pulp", name)
        upload_f = f_flat_map(f_return(), lambda _: do_next_upload(hashlib.sha256(), 0))

        if not is_file_object:
            upload_f.add_done_callback(lambda _: file_obj.close())
        return upload_f

    def _publish_repository(self, repo, distributors_with_config):
        tasks_f = f_return([])

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

    def _do_unassociate(self, repo_id, criteria=None):
        url = os.path.join(
            self._url, "pulp/api/v2/repositories/%s/actions/unassociate/" % repo_id
        )

        # use type hint=Unit so that if type_ids are the goal here
        # then we will get back a properly prepared PulpSearch with
        # a populated type_ids field
        pulp_search = search_for_criteria(criteria, type_hint=Unit, type_ids_accum=None)

        body = {"criteria": {"type_ids": pulp_search.type_ids}}

        LOG.debug("Submitting %s unassociate: %s", url, body)

        return self._task_executor.submit(
            self._do_request, method="POST", url=url, json=body
        )

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

    def _request_upload(self):
        url = os.path.join(self._url, "pulp/api/v2/content/uploads/")

        LOG.debug("Requesting upload id")
        return self._request_executor.submit(self._do_request, method="POST", url=url)

    def _do_upload(self, data, upload_id, offset):
        url = os.path.join(
            self._url, "pulp/api/v2/content/uploads/%s/%s/" % (upload_id, offset)
        )

        return self._request_executor.submit(
            self._do_request, method="PUT", url=url, data=data
        )

    def _do_import(self, repo_id, upload_id, unit_type_id, unit_key):
        url = os.path.join(
            self._url, "pulp/api/v2/repositories/%s/actions/import_upload/" % repo_id
        )

        body = {
            "unit_type_id": unit_type_id,
            "upload_id": upload_id,
            "unit_key": unit_key,
        }

        LOG.debug("Importing contents to repo %s with upload id %s", repo_id, upload_id)
        return self._task_executor.submit(
            self._do_request, method="POST", url=url, json=body
        )

    def _delete_upload_request(self, upload_id):
        url = os.path.join(self._url, "pulp/api/v2/content/uploads/%s/" % upload_id)

        LOG.debug("Deleting upload request %s", upload_id)
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
