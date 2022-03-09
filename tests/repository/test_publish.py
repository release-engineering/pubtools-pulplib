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
)

from pubtools.pluggy import pm


@pytest.fixture
def hookspy():
    hooks = []

    def record_hook(hook_name, _hook_impls, kwargs):
        hooks.append((hook_name, kwargs))

    def do_nothing(*args, **kwargs):
        pass

    undo = pm.add_hookcall_monitoring(before=record_hook, after=do_nothing)
    yield hooks
    undo()


def test_detached():
    """publish raises if called on a detached repo"""
    with pytest.raises(DetachedException):
        Repository(id="some-repo").publish()


def test_publish_no_distributors(client):
    """publish succeeds and returns no tasks if repo contains no distributors."""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client

    assert repo.publish().result() == []


def test_publish_distributors(fast_poller, requests_mocker, client, hookspy):
    """publish succeeds and returns tasks from each applicable distributor"""
    repo = YumRepository(
        id="some-repo",
        distributors=(
            Distributor(id="yum_distributor", type_id="yum_distributor"),
            Distributor(id="other_distributor", type_id="other_distributor"),
            Distributor(id="cdn_distributor", type_id="rpm_rsync_distributor"),
        ),
    )
    repo.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/publish/",
        [
            {"json": {"spawned_tasks": [{"task_id": "task1"}, {"task_id": "task2"}]}},
            {"json": {"spawned_tasks": [{"task_id": "task3"}]}},
        ],
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        [
            {
                "json": [
                    {"task_id": "task1", "state": "finished"},
                    {"task_id": "task2", "state": "skipped"},
                ]
            },
            {"json": [{"task_id": "task3", "state": "finished"}]},
        ],
    )

    # It should have succeeded, with the tasks as retrieved from Pulp
    assert sorted(repo.publish()) == [
        Task(id="task1", succeeded=True, completed=True),
        Task(id="task2", succeeded=True, completed=True),
        Task(id="task3", succeeded=True, completed=True),
    ]

    # It should have first issued a request to publish yum_distributor
    req = requests_mocker.request_history
    assert (
        req[0].url
        == "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/publish/"
    )
    assert req[0].json() == {"id": "yum_distributor", "override_config": {}}

    # Then polled for resulting tasks to succeed
    assert req[1].url == "https://pulp.example.com/pulp/api/v2/tasks/search/"
    assert req[1].json() == {
        "criteria": {"filters": {"task_id": {"$in": ["task1", "task2"]}}}
    }

    # Then published the next distributor
    assert (
        req[2].url
        == "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/publish/"
    )
    assert req[2].json() == {"id": "cdn_distributor", "override_config": {}}

    # Then waited for those tasks to finish too
    assert req[3].url == "https://pulp.example.com/pulp/api/v2/tasks/search/"
    assert req[3].json() == {"criteria": {"filters": {"task_id": {"$in": ["task3"]}}}}

    # And there should have been no more requests
    assert len(req) == 4

    # It should have invoked hooks
    assert len(hookspy) == 2
    (hook_name, hook_kwargs) = hookspy[0]
    assert hook_name == "pulp_repository_pre_publish"
    assert hook_kwargs["repository"] is repo
    assert hook_kwargs["options"] == PublishOptions()
    (hook_name, hook_kwargs) = hookspy[1]
    assert hook_name == "pulp_repository_published"
    assert hook_kwargs["repository"] is repo
    assert hook_kwargs["options"] == PublishOptions()


def test_publish_with_options(requests_mocker, client):
    """publish passes expected config into distributors based on publish options"""
    repo = YumRepository(
        id="some-repo",
        distributors=(
            Distributor(id="yum_distributor", type_id="yum_distributor"),
            Distributor(id="cdn_distributor", type_id="rpm_rsync_distributor"),
        ),
    )
    repo.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/publish/",
        [
            {"json": {"spawned_tasks": [{"task_id": "task1"}]}},
            {"json": {"spawned_tasks": [{"task_id": "task2"}]}},
        ],
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        [
            {"json": [{"task_id": "task1", "state": "finished"}]},
            {"json": [{"task_id": "task2", "state": "finished"}]},
        ],
    )

    options = PublishOptions(
        clean=True, force=True, origin_only=True, rsync_extra_args=["-a"]
    )

    # It should have succeeded, with the tasks as retrieved from Pulp
    assert sorted(repo.publish(options)) == [
        Task(id="task1", succeeded=True, completed=True),
        Task(id="task2", succeeded=True, completed=True),
    ]

    req = requests_mocker.request_history

    # The yum_distributor request should have set force_full, but not
    # delete since it's not recognized by that distributor
    assert req[0].json()["override_config"] == {"force_full": True}

    # The cdn_distributor request should have set force_full, delete
    # and content_units_only
    assert req[2].json()["override_config"] == {
        "force_full": True,
        "delete": True,
        "content_units_only": True,
        "rsync_extra_args": ["-a"],
    }


def test_publish_fail(fast_poller, requests_mocker, client):
    """publish raises TaskFailedException if publish task fails"""
    repo = YumRepository(
        id="some-repo",
        distributors=(Distributor(id="yum_distributor", type_id="yum_distributor"),),
    )
    repo.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/publish/",
        json={"spawned_tasks": [{"task_id": "task1"}]},
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        json=[
            {
                "task_id": "task1",
                "state": "error",
                "error": {"code": "ABC00123", "description": "Simulated error"},
            }
        ],
    )

    publish_f = repo.publish()

    # It should raise this exception
    with pytest.raises(TaskFailedException) as error:
        publish_f.result()

    # The exception should have a reference to the task which failed
    assert error.value.task.id == "task1"
    assert "Pulp task [task1] failed: ABC00123: Simulated error" in str(error.value)


def test_publish_broken_response(fast_poller, requests_mocker, client):
    """publish raises an exception if Pulp /publish/ responded with parseable
    JSON, but not of the expected structure
    """

    repo = YumRepository(
        id="some-repo",
        distributors=(Distributor(id="yum_distributor", type_id="yum_distributor"),),
    )
    repo.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/publish/",
        json={"spawned_tasks": ["oops, not a valid response"]},
    )

    publish_f = repo.publish()

    # It should raise some kind of exception due to the invalid spawned_tasks structure
    assert publish_f.exception()


def test_publish_retries(fast_poller, requests_mocker, client, caplog):
    """publish retries distributors as they fail"""
    caplog.set_level(logging.WARNING)

    repo = YumRepository(
        id="some-repo",
        distributors=(
            Distributor(id="yum_distributor", type_id="yum_distributor"),
            Distributor(id="cdn_distributor", type_id="cdn_distributor"),
        ),
    )
    repo.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/publish/",
        [
            {"json": {"spawned_tasks": [{"task_id": "task1"}]}},
            {"json": {"spawned_tasks": [{"task_id": "task2"}]}},
            {"json": {"spawned_tasks": [{"task_id": "task3"}]}},
        ],
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        [
            {"json": [{"task_id": "task1", "state": "finished"}]},
            {"json": [{"task_id": "task2", "state": "error"}]},
            {"json": [{"task_id": "task3", "state": "finished"}]},
        ],
    )

    publish_f = repo.publish()

    # It should succeed
    tasks = publish_f.result()

    # It should return only the *successful* tasks
    assert sorted([t.id for t in tasks]) == ["task1", "task3"]

    # Pick out the HTTP requests triggering distributors
    publish_reqs = [
        req
        for req in requests_mocker.request_history
        if req.url
        == "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/publish/"
    ]
    publish_distributors = [req.json()["id"] for req in publish_reqs]

    # It should have triggered cdn_distributor twice, since the first attempt failed
    assert publish_distributors == [
        "yum_distributor",
        "cdn_distributor",
        "cdn_distributor",
    ]

    # The retry should have been logged
    messages = caplog.messages
    assert (
        messages[-1].splitlines()[0] == "Retrying due to error: Task task2 failed [1/6]"
    )
