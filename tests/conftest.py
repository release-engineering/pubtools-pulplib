import os

import pytest
import requests_mock

from pubtools.pulplib import Client
from pubtools.pulplib._impl.client.poller import TaskPoller
from pubtools.pulplib._impl.client.retry import PulpRetryPolicy


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
    """Yields a preconfigured Client instance.

    - client points at https://pulp.example.com/
    - client has a retry policy configured so that all sleeps are very fast
      (avoids delays due to retry in autotests)
    """
    with FastRetryClient("https://pulp.example.com/") as client:
        yield client


@pytest.fixture
def fast_poller():
    """Overrides TaskPoller behavior to retry much faster than it otherwise
    would.

    Use this fixture to speed up tests which would otherwise have to spend
    a significant amount of time waiting on polls.
    """
    old_max_attempts = TaskPoller.MAX_ATTEMPTS
    old_delay = TaskPoller.DELAY

    TaskPoller.MAX_ATTEMPTS = 10
    TaskPoller.DELAY = 0.001

    yield

    TaskPoller.MAX_ATTEMPTS = old_max_attempts
    TaskPoller.DELAY = old_delay


@pytest.fixture
def data_path():
    """Returns path to the tests/data dir used to store extra files for testing."""

    return os.path.join(os.path.dirname(__file__), "data")


class FastRetryPolicy(PulpRetryPolicy):
    def __init__(self):
        super(FastRetryPolicy, self).__init__(max_attempts=6, max_sleep=0.001)


class FastRetryClient(Client):
    _RETRY_POLICY = FastRetryPolicy()
