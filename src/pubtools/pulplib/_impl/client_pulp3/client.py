# Generated-by: Claude Code

from json import JSONDecodeError
import logging
import os
from typing import Any, Dict, Optional, Union, Tuple
from urllib.parse import urljoin

import anyio
import httpx
from .errors import Pulp3TaskException
from .retry import get_retry_policy

LOG = logging.getLogger("pubtools.pulplib")


class Pulp3Client:
    """An async client for the Pulp 3.x API.

    This class provides high-level async methods for querying a Pulp 3 server
    and performing actions in Pulp.

    **Usage:**

    This client is designed to be used as an async context manager with AnyIO's
    Trio backend:

    .. code-block:: python

        async with Pulp3Client(url="https://pulp.example.com/") as client:
            repo = await client.create_repository("test-repo")
            print(repo["name"])

    **Backend:**

    The client uses:
    - AnyIO with Trio backend for structured concurrency
    - httpx for async HTTP requests
    - Task groups for managing concurrent operations

    **Rate Limiting:**

    The client supports automatic rate limiting to avoid overwhelming the server.
    """

    _DEFAULT_TIMEOUT = 120.0
    _MAX_CONCURRENT_REQUESTS = int(
        os.environ.get("PUBTOOLS_PULPLIB_MAX_CONCURRENT_REQUESTS", "10")
    )

    def __init__(
        self,
        url: str,
        auth: Optional[tuple] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        verify: bool = True,
        timeout: Optional[float] = None,
        max_retries: int = 5,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 60.0,
        domain: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            url: URL of a Pulp 3 server, e.g. https://pulp.example.com/
            auth: Optional tuple of (username, password) for authentication
            cert: Optional path to client certificate file
            verify: Whether to verify SSL certificates (default: True)
            timeout: Request timeout in seconds (default: 120.0)
            max_retries: Maximum retry attempts for failed requests (default: 5)
            retry_min_wait: Minimum wait between retries in seconds (default: 1.0)
            retry_max_wait: Maximum wait between retries in seconds (default: 60.0)
            domain: Pulp domain name (default: from PULP_DOMAIN env or 'default')
            **kwargs: Additional arguments passed to httpx.AsyncClient
        """
        # Set domain and API path
        self._domain = domain or os.getenv("PULP_DOMAIN", "default")
        self._api_path = f"/api/pulp/{self._domain}/api/v3/"

        # Construct full API URL
        self._url = urljoin(url.rstrip("/"), self._api_path)
        self._auth = httpx.BasicAuth(*auth) if auth else None
        self._cert = cert
        self._verify = verify
        self._timeout = timeout or self._DEFAULT_TIMEOUT
        self._retry_policy = get_retry_policy(
            max_attempts=max_retries,
            min_wait=retry_min_wait,
            max_wait=retry_max_wait,
        )
        self._client_kwargs = kwargs

        self._client: Optional[httpx.AsyncClient] = None
        self._limiter: Optional[anyio.CapacityLimiter] = None

    async def __aenter__(self):
        """Enter async context manager."""
        self._limiter = anyio.CapacityLimiter(self._MAX_CONCURRENT_REQUESTS)

        self._client = httpx.AsyncClient(
            base_url=self._url,
            auth=self._auth,
            cert=self._cert,
            verify=self._verify,
            timeout=self._timeout,
            **self._client_kwargs,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._limiter = None

    async def _do_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Execute HTTP request without retry logic.

        Args:
            method: HTTP method
            url: Full URL
            **kwargs: Arguments for httpx request

        Returns:
            HTTP response
        """
        LOG.debug("%s %s", method, url)
        response = await self._client.request(method, url, **kwargs)
        LOG.debug("Response %s %s: %s", method, url, response.status_code)
        response.raise_for_status()
        return response

    async def _request(
        self, method: str, path: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Make an HTTP request to Pulp API with retry and rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (will be joined with base URL)
            **kwargs: Additional arguments passed to httpx request

        Returns:
            Parsed JSON response, or None if resource not found (404)

        Raises:
            httpx.HTTPStatusError: For HTTP errors (except 404)
            httpx.HTTPError: For network/connection errors
            RuntimeError: If client not initialized
        """
        if not self._client:
            raise RuntimeError(
                "Client not initialized. Use 'async with' context manager."
            )

        url = urljoin(self._url + "/", path.lstrip("/"))

        async with self._limiter:
            try:
                async for attempt in self._retry_policy:
                    with attempt:
                        response = await self._do_request(method, url, **kwargs)

                        # Handle 204 No Content
                        if response.status_code == 204:
                            return None

                        # Parse JSON response
                        try:
                            return response.json()
                        except JSONDecodeError as e:
                            LOG.error(
                                "Failed to decode JSON from %s %s: %s", method, url, e
                            )
                            LOG.debug("Response body: %s", response.text[:500])
                            raise

            except httpx.HTTPStatusError as e:
                # Handle 404 as a special case - resource not found is valid
                if e.response.status_code == 404:
                    LOG.debug("Resource not found: %s %s", method, url)
                    return None
                raise

    async def get_status(self) -> Dict[str, Any]:
        """Get Pulp server status.

        Returns:
            Dictionary containing server status information
        """
        return await self._request("GET", "/status/")

    async def create_repository(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new repository.

        Args:
            name: Repository name
            **kwargs: Additional repository attributes (description, retain_repo_versions, etc.)

        Returns:
            Created repository data
        """
        LOG.info("Creating repository: %s", name)
        data = {"name": name, **kwargs}
        path = "/repositories/rpm/rpm/"
        result = await self._request("POST", path, json=data)
        LOG.info("Repository created: %s (href: %s)", name, result.get("pulp_href"))
        return result

    async def poll_task(
        self,
        task_href_or_id: str,
        poll_interval: float = 5.0,
        timeout: float = 60.0 * 60,  # 1 hour
    ) -> Dict[str, Any]:
        """Poll a task until completion.

        Args:
            task_href_or_id: Task href (e.g., '/api/pulp/.../tasks/abc/') or task ID (e.g., 'abc')
            poll_interval: Seconds between poll attempts (default: 5.0)
            timeout: Maximum time to wait in seconds (default: 3600.0 / 1 hour)

        Returns:
            Completed task data dictionary

        Raises:
            Pulp3TaskException: If task fails or is canceled
            TimeoutError: If timeout is exceeded
        """
        task_id = (
            task_href_or_id.split("/")[-2]
            if task_href_or_id.startswith("/api/")
            else task_href_or_id
        )

        async def _poll():
            while True:
                task = await self._request("GET", f"/tasks/{task_id}/")
                state = task.get("state")

                if state == "completed":
                    LOG.info("Task %s completed", task_id)
                    return task
                elif state in ("failed", "canceled"):
                    error = task.get("error", {}).get("description", "Unknown error")
                    LOG.error("Task %s %s: %s", task_id, state, error)
                    raise Pulp3TaskException(f"Task {task_id} {state}: {error}")

                LOG.debug("Task %s state: %s", task_id, state)
                await anyio.sleep(poll_interval)

        with anyio.fail_after(timeout):
            return await _poll()

    async def create_publication(self, repository_href: str, **kwargs) -> str:
        """Create a publication for a repository.

        Args:
            repository_href: Repository href to publish
            **kwargs: Additional publish options

        Returns:
            Task href string (e.g., '/api/pulp/.../tasks/abc/')

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        LOG.info("Creating publication for repository: %s", repository_href)
        data = {"repository": repository_href, **kwargs}
        result = await self._request("POST", "/publications/rpm/rpm/", json=data)
        LOG.debug("Publication task created: %s", result.get("task"))
        return result.get("task")

    async def modify_repo_content(
        self,
        repository_href_or_id: str,
        add_content_units: Optional[list] = None,
        remove_content_units: Optional[list] = None,
    ) -> str:
        """Modify repository content by adding or removing content units.

        Args:
            repository_href_or_id: Repository href (e.g., '/api/.../repositories/rpm/rpm/abc/')
                                   or repository ID (e.g., 'abc')
            add_content_units: List of content unit hrefs to add (default: None)
            remove_content_units: List of content unit hrefs to remove (default: None)

        Returns:
            Task href string (e.g., '/api/pulp/.../tasks/xyz/')

        Raises:
            ValueError: If both add_content_units and remove_content_units are empty
            httpx.HTTPStatusError: If request fails
        """
        LOG.info(
            "Modifying repository content: %s (add: %d, remove: %d)",
            repository_href_or_id,
            len(add_content_units or []),
            len(remove_content_units or []),
        )
        if not add_content_units and not remove_content_units:
            raise ValueError(
                f"No content to modify for repository: {repository_href_or_id}"
            )

        repository_id = (
            repository_href_or_id.split("/")[-2]
            if repository_href_or_id.startswith("/api/")
            else repository_href_or_id
        )
        path = os.path.join(f"repositories/rpm/rpm/{repository_id}/", "modify/")

        data = {
            "add_content_units": add_content_units or [],
            "remove_content_units": remove_content_units or [],
        }
        result = await self._request("POST", path, json=data)
        LOG.debug("Content modification task created: %s", result.get("task"))
        return result.get("task")

    async def create_distribution(
        self, repository_href: str, base_path: str, name: str
    ) -> str:
        """Create a distribution for a repository.

        Args:
            repository_href: Repository href to add distribution
            base_path: Base path for the distribution (URL path component)
            name: Name of the distribution

        Returns:
            Task href string (e.g., '/api/pulp/.../tasks/xyz/')

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        LOG.info(
            "Creating distribution: %s at %s for repository %s",
            name,
            base_path,
            repository_href,
        )
        url = "/distributions/rpm/rpm/"
        data = {
            "base_path": base_path,
            "name": name,
            "repository": repository_href,
        }

        result = await self._request("POST", url, json=data)
        LOG.debug("Distribution task created: %s", result.get("task"))
        return result.get("task")

    def build_query_sha256(self, checksums: list) -> str:
        """Build a Pulp query for searching content by SHA256 checksums.

        Args:
            checksums: List of SHA256 checksum strings

        Returns:
            Query string suitable for search_content(), e.g., "(sha256=abc OR sha256=def)"

        Example:
            >>> client.build_query_sha256(["abc123", "def456"])
            '(sha256=abc123 OR sha256=def456)'

        Note:
            This method will be refactored/reimplemented to support generic field queries in the future.
        """
        query = ""
        for i, checksum in enumerate(checksums):
            if i:
                query += " OR "
            query += f"sha256={checksum}"

        query = f"({query})"

        return query

    async def search_content(
        self,
        query: str,
        fields: Optional[list] = None,
        offset: int = 0,
        limit: int = 1000,
    ) -> list:
        """Search for RPM package content.

        Args:
            query: Query string (e.g., from build_query_sha256)
            fields: Optional list of field names to return (default: all fields)
            offset: Offset for pagination (default: 0)
            limit: Limit for pagination (default: 1000)
        Returns:
            List of matching content unit dictionaries

        Raises:
            httpx.HTTPStatusError: If request fails

        Note:
            This method currently does not support pagination automatically.
            Use offset/limit in params for manual pagination.
        """
        url = "content/rpm/packages/"
        params = {"q": query, "offset": offset, "limit": limit}
        if fields:
            params["fields"] = ",".join(fields)
        data = await self._request("GET", url, params=params)
        return data.get("results", []) if data else []
