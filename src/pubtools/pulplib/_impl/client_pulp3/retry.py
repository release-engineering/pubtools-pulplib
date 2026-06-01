# Generated-by: Claude Code

import logging

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

LOG = logging.getLogger("pubtools.pulplib")


def should_retry_request(exception: Exception) -> bool:
    """Determine if an HTTP request should be retried.

    Args:
        exception: Exception that occurred

    Returns:
        True if request should be retried
    """
    if isinstance(exception, httpx.HTTPStatusError):
        status_code = exception.response.status_code
        # Retry on timeout, rate limiting, and server errors
        return status_code in (408, 429, 500, 502, 503, 504, 400)

    if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError)):
        return True

    return False


def get_retry_policy(
    max_attempts: int = 5,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
) -> AsyncRetrying:
    """Create a tenacity retry policy for Pulp API requests.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries in seconds
        max_wait: Maximum wait time between retries in seconds

    Returns:
        Configured AsyncRetrying instance
    """
    return AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(min=min_wait, max=max_wait),
        retry=retry_if_exception(should_retry_request),
        before_sleep=before_sleep_log(LOG, logging.WARNING),
        reraise=True,
    )
