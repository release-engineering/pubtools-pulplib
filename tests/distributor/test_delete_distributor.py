import pytest

from pubtools.pulplib import Repository, Distributor, Task, DetachedException


def test_detached_noclient():
    """delete raises if called on a distributor without client"""
    with pytest.raises(DetachedException):
        Distributor(
            id="some-dist", type_id="some-dist-type", repo_id="some-repo"
        ).delete()


def test_detached_norepo(client):
    """delete raises if called on a distributor without repo"""
    with pytest.raises(DetachedException):
        dist = Distributor(id="some-dist", type_id="some-dist-type")
        dist._set_client(client)
        dist.delete()


def test_delete_success(fast_poller, requests_mocker, client):
    """delete succeeds and returns spawned tasks"""

    repo = Repository(
        id="some-repo",
        distributors=[
            Distributor(id="dist1", type_id="type1", repo_id="some-repo"),
            Distributor(id="dist2", type_id="type2", repo_id="some-repo"),
        ],
    )
    repo._set_client(client)

    requests_mocker.delete(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/distributors/dist1/",
        json={"spawned_tasks": [{"task_id": "task1"}, {"task_id": "task2"}]},
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        json=[
            {"task_id": "task1", "state": "finished"},
            {"task_id": "task2", "state": "skipped"},
        ],
    )

    # It should succeed, with the tasks as retrieved from Pulp
    dist = repo.distributors[0]
    delete_dist = dist.delete()
    assert sorted(delete_dist) == [
        Task(id="task1", succeeded=True, completed=True),
        Task(id="task2", succeeded=True, completed=True),
    ]

    # And should now be detached
    with pytest.raises(DetachedException):
        dist.delete()
