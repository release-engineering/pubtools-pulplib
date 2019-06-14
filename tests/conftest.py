import logging
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


class CaplogCompat(object):
    def __init__(self, delegate):
        self._delegate = delegate
        self._level = logging.INFO

    def __getattr__(self, name):
        return getattr(self._delegate, name)

    def set_level(self, level, logger=None):
        self._level = level
        return self._delegate.setLevel(level, logger)

    def clear(self):
        import py.io

        handler = self._delegate.handler
        handler.stream = py.io.TextIO()
        handler.records = []

    @property
    def records(self):
        recs = self._delegate.records()
        return [rec for rec in recs if rec.levelno >= self._level]

    @property
    def messages(self):
        records = self.records
        return [rec.message for rec in records]


@pytest.fixture
def caplog_compat(caplog):
    """Just like caplog but also works with pytest-capturelog, patching
    API slightly to make it compatible
    """
    if "set_level" in dir(caplog):
        return caplog
    return CaplogCompat(caplog)


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


class FastRetryPolicy(PulpRetryPolicy):
    def __init__(self):
        super(FastRetryPolicy, self).__init__(max_attempts=6, max_sleep=0.001)


class FastRetryClient(Client):
    _RETRY_POLICY = lambda *_: FastRetryPolicy()
