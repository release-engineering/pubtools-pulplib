import datetime
import pytest

from pubtools.pulplib import Repository, Task, DetachedException


def test_detached():
    """delete raises if called on a detached repo"""
    with pytest.raises(DetachedException):
        Repository(id="some-repo").delete()


def test_delete_success(fast_poller, requests_mocker, client):
    """delete succeeds and returns spawned tasks"""

    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client

    requests_mocker.delete(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/",
        json={"spawned_tasks": [{"task_id": "task1"}, {"task_id": "task2"}]},
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        json=[
            {"task_id": "task1", "state": "finished"},
            {"task_id": "task2", "state": "skipped"},
        ],
    )

    # It should have succeeded, with the tasks as retrieved from Pulp
    assert sorted(repo.delete().result()) == [
        Task(id="task1", succeeded=True, completed=True),
        Task(id="task2", succeeded=True, completed=True),
    ]


def test_delete_detaches(fast_poller, requests_mocker, client):
    """delete causes repository to become detached"""

    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client

    requests_mocker.delete(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/",
        json={"spawned_tasks": [{"task_id": "task1"}, {"task_id": "task2"}]},
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        json=[
            {"task_id": "task1", "state": "finished"},
            {"task_id": "task2", "state": "skipped"},
        ],
    )

    # Delete should succeed
    repo.delete().result()

    # Second attempt to delete doesn't make sense
    with pytest.raises(DetachedException):
        repo.delete()
