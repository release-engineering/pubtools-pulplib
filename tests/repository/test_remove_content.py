import logging
import pytest

from pubtools.pulplib import (
    Repository,
    YumRepository,
    Task,
    Distributor,
    DetachedException,
    PublishOptions,
    TaskFailedException,
    RpmUnit,
    FileUnit,
    ModulemdUnit,
    YumRepoMetadataFileUnit,
    Unit,
)


def test_detached():
    """remove_content raises if called on a detached repo"""
    with pytest.raises(DetachedException):
        Repository(id="some-repo").remove_content()


def test_remove_no_type_ids(fast_poller, requests_mocker, client):
    """Remove succeeds when given no type_ids."""

    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/unassociate/",
        [{"json": {"spawned_tasks": [{"task_id": "task1"}, {"task_id": "task2"}]}}],
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        [
            {
                "json": [
                    {"task_id": "task1", "state": "finished"},
                    {"task_id": "task2", "state": "skipped"},
                ]
            }
        ],
    )

    assert repo.remove_content().result() == [
        Task(id="task1", completed=True, succeeded=True),
        Task(id="task2", completed=True, succeeded=True),
    ]


def test_remove_with_type_ids(fast_poller, requests_mocker, client):
    """Remove succeeds when given specific type_ids."""

    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/unassociate/",
        [{"json": {"spawned_tasks": [{"task_id": "task1"}]}}],
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        [{"json": [{"task_id": "task1", "state": "finished"}]}],
    )

    assert repo.remove_content(type_ids=["type1", "type2"]).result() == [
        Task(id="task1", completed=True, succeeded=True)
    ]

    # It should have passed those type_ids to Pulp
    req = requests_mocker.request_history
    assert (
        req[0].url
        == "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/unassociate/"
    )
    assert req[0].json() == {"criteria": {"type_ids": ["type1", "type2"]}}


def test_remove_loads_units(fast_poller, requests_mocker, client):
    """Remove returns unit info loaded from units_successful."""

    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/unassociate/",
        [{"json": {"spawned_tasks": [{"task_id": "task1"}]}}],
    )

    unit_data = [
        {
            "type_id": "iso",
            "unit_key": {"name": "hello.txt", "size": 23, "checksum": "a" * 64},
        },
        {
            "type_id": "rpm",
            "unit_key": {
                "name": "bash",
                "epoch": "0",
                "version": "4.0",
                "release": "1",
                "arch": "x86_64",
            },
        },
        {
            "type_id": "modulemd",
            "unit_key": {
                "name": "module",
                "stream": "s1",
                "version": 1234,
                "context": "a1b2c3",
                "arch": "s390x",
            },
        },
        {
            "type_id": "yum_repo_metadata_file",
            "unit_key": {"data_type": "productid", "repo_id": "some-repo"},
        },
        {"type_id": "bizarre_type", "unit_key": {"whatever": "data"}},
    ]

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        [
            {
                "json": [
                    {
                        "task_id": "task1",
                        "state": "finished",
                        "result": {"units_successful": unit_data},
                    }
                ]
            }
        ],
    )

    tasks = repo.remove_content().result()

    # It should return one task
    assert len(tasks) == 1
    task = tasks[0]

    # It should be the expected successful task
    assert task.id == "task1"
    assert task.completed
    assert task.succeeded

    # It should have loaded expected units from the units_successful dict
    assert set(task.units) == set(
        [
            FileUnit(path="hello.txt", size=23, sha256sum="a" * 64),
            RpmUnit(
                name="bash",
                epoch="0",
                version="4.0",
                release="1",
                arch="x86_64",
                sourcerpm=None,
            ),
            ModulemdUnit(
                name="module", stream="s1", version=1234, context="a1b2c3", arch="s390x"
            ),
            YumRepoMetadataFileUnit(
                data_type="productid", content_type_id="yum_repo_metadata_file"
            ),
            Unit(content_type_id="bizarre_type"),
        ]
    )
