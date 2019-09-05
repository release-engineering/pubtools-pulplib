import os
import logging
import threading
import hashlib
import json
from functools import partial
import six
from six.moves import StringIO

import requests
from more_executors import Executors
from more_executors.futures import f_map, f_flat_map, f_return

from ..page import Page
from ..criteria import Criteria
from ..model import Repository, MaintenanceReport
from .search import filters_for_criteria
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
            Executors.thread_pool(max_workers=self._REQUEST_THREADS)
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
            Executors.thread_pool(max_workers=self._REQUEST_THREADS)
            .with_map(self._unpack_response)
            .with_map(self._log_spawned_tasks)
            .with_poll(poller, cancel_fn=poller.cancel)
            .with_throttle(self._TASK_THROTTLE)
            .with_retry(retry_policy=self._RETRY_POLICY)
        )

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
        return repo_f

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
        pulp_crit = {
            "skip": 0,
            "limit": self._PAGE_SIZE,
            "filters": filters_for_criteria(criteria, Repository),
        }
        search = {"criteria": pulp_crit, "distributors": True}

        response_f = self._do_search("repositories", search)

        # When this request is resolved, we'll have the first page of data.
        # We'll need to convert that into a page and also keep going with
        # the search if there's more to be done.
        return f_map(
            response_f, lambda data: self._handle_page(Repository, search, data)
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
        return f_map(out, lambda types: sorted([t["id"] for t in types]))

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

    def _do_unassociate(self, repo_id, type_ids):
        url = os.path.join(
            self._url, "pulp/api/v2/repositories/%s/actions/unassociate/" % repo_id
        )

        body = {}
        if type_ids is not None:
            body["type_ids"] = type_ids

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

    def _handle_page(self, object_class, search, raw_data):
        LOG.debug("Got pulp response for %s, %s elems", search, len(raw_data))

        page_data = [object_class.from_data(elem) for elem in raw_data]
        for obj in page_data:
            obj.__dict__["_client"] = self

        # Do we need a next page?
        next_page = None

        limit = search["criteria"]["limit"]
        if len(raw_data) == limit:
            # Yeah, we might...
            search = search.copy()
            search["criteria"] = search["criteria"].copy()
            search["criteria"]["skip"] = search["criteria"]["skip"] + limit
            response_f = self._do_search("repositories", search)
            next_page = f_map(
                response_f, lambda data: self._handle_page(object_class, search, data)
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

    def _do_search(self, resource_type, search):
        url = os.path.join(self._url, "pulp/api/v2/{0}/search/".format(resource_type))

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
            if hasattr(exception, "response") and exception.response.status_code == 404:
                return None
            # Any other types of errors are raised unchanged.
            raise exception

        url = os.path.join(self._url, "pulp/isos/redhat-maintenance/repos.json")

        response = self._request_executor.submit(
            self._do_request, method="GET", url=url
        )

        return f_map(response, error_fn=map_404_to_none)
