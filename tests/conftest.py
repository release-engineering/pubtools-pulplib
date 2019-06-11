from more_executors.retry import ExceptionRetryPolicy
import pytest
import requests_mock

from pubtools.pulplib import Client
from pubtools.pulplib._impl.client.poller import TaskPoller


@pytest.fixture
def requests_mocker():
    """Yields a new requests_mock Mocker.

    This is the same as using Mocker as a function decorator, but instead
    uses the pytest fixture system.
    """
    with requests_mock.Mocker() as mocker:
        yield mocker


@pytest.fixture
def client():
    return FastRetryClient("https://pulp.example.com/")


@pytest.fixture
def fast_poller():
    old_max_attempts = TaskPoller.MAX_ATTEMPTS
    old_delay = TaskPoller.DELAY

    TaskPoller.MAX_ATTEMPTS = 10
    TaskPoller.DELAY = 0.001

    yield

    TaskPoller.MAX_ATTEMPTS = old_max_attempts
    TaskPoller.DELAY = old_delay


def fast_retry_policy(_client):
    return ExceptionRetryPolicy(max_attempts=6, max_sleep=0.001)


class FastRetryClient(Client):
    _RETRY_POLICY = fast_retry_policy
