import pytest

from concurrent.futures import ThreadPoolExecutor

from pubtools.pulplib import Client


@pytest.fixture
def spy_requested_threads(monkeypatch):
    """This fixture intercepts all ThreadPoolExecutor.__init__ calls
    to spy on the number of requested threads.

    Yields a list which will gain a new element every time an executor
    is created, the element being the executor's max_workers parameter.
    """

    requested_threads = []
    executor_ctor = ThreadPoolExecutor.__init__

    def spy_requested_threads(*args, **kwargs):
        requested_threads.append(kwargs.get("max_workers"))
        return executor_ctor(*args, **kwargs)

    monkeypatch.setattr(ThreadPoolExecutor, "__init__", spy_requested_threads)

    yield requested_threads


def test_at_least_one_thread(spy_requested_threads):
    """Client always enforces at least one thread (per pool)"""

    with Client("https://pulp.example.com/", threads=-5) as client:
        pass

    # Everything should have used a single thread each
    assert set(spy_requested_threads) == set([1])


def test_threads(spy_requested_threads):
    """Caller's requested 'threads' are passed into any internal ThreadPoolExecutors."""

    with Client("https://pulp.example.com/", threads=3) as client:
        pass

    # Everything should have used the requested number of threads
    assert set(spy_requested_threads) == set([3])
