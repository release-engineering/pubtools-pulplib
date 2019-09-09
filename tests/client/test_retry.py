import requests
from more_executors.futures import f_return_error

from pubtools.pulplib._impl.client.retry import PulpRetryPolicy


def test_retries_by_default():
    """Retry policy will retry on generic exception types."""
    policy = PulpRetryPolicy()
    assert policy.should_retry(0, f_return_error(RuntimeError("oops!")))


def test_retries_http_errors():
    """Retry policy will retry on HTTP-level errors."""
    policy = PulpRetryPolicy()
    response = requests.Response()
    response.status_code = 500
    error = requests.HTTPError(response=response)
    assert policy.should_retry(0, f_return_error(error))


def test_retries_http_errors_no_response():
    """Retry policy will retry on requests exception types with response=None."""
    policy = PulpRetryPolicy()
    error = requests.HTTPError(response=None)
    assert policy.should_retry(0, f_return_error(error))


def test_no_retries_http_404_errors():
    """Retry policy does not retry on HTTP 404 responses."""
    policy = PulpRetryPolicy()
    response = requests.Response()
    response.status_code = 404
    error = requests.HTTPError(response=response)
    assert not policy.should_retry(0, f_return_error(error))
