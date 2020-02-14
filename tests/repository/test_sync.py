import logging
import pytest

from pubtools.pulplib import (
    Repository,
    YumRepository,
    Task,
    Distributor,
    DetachedException,
    YumSyncOptions,
    TaskFailedException,
)


@pytest.fixture
def fixture_sync_async_response(requests_mocker):
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/sync/",
        [{"json": {"spawned_tasks": [{"task_id": "task1"}]}}],
    )


@pytest.fixture
def fixture_search_task_response(requests_mocker):
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        [{"json": [{"task_id": "task1", "state": "finished"}]}],
    )


def test_detached():
    """sync raises if called on a detached repo"""
    with pytest.raises(DetachedException):
        Repository(id="some-repo").sync()


def test_sync_no_feed(
    fast_poller,
    client,
    requests_mocker,
    fixture_sync_async_response,
    fixture_search_task_response,
):
    """Test sync fail as no feed is provided."""
    repo = YumRepository(id="some-repo")
    repo.__dict__["_client"] = client

    # empty options should fail as feed is required to be non-empty
    try:
        repo.sync().result()
        assert "Exception should have been raised"
    except ValueError:
        pass


def test_sync_with_options(
    requests_mocker, client, fixture_sync_async_response, fixture_search_task_response
):
    """Test sync passes, test whether sync options are passed to override config."""
    repo = YumRepository(id="some-repo")
    repo.__dict__["_client"] = client

    options = YumSyncOptions(ssl_validation=False, feed="mock://example.com/")

    # It should have succeeded, with the tasks as retrieved from Pulp
    assert repo.sync(options).result() == [
        Task(id="task1", succeeded=True, completed=True)
    ]

    req = requests_mocker.request_history

    assert req[0].json()["override_config"] == {
        "ssl_validation": False,
        "feed": "mock://example.com/",
    }
