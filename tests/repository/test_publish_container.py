from pubtools.pulplib import ContainerImageRepository, Distributor, PublishOptions, Task


def test_publish_order(requests_mocker, client):
    """publish runs docker/rsync distributors in correct order"""
    repo = ContainerImageRepository(
        id="some-repo",
        distributors=(
            Distributor(
                id="docker_web_distributor_name_cli", type_id="docker_distributor_web"
            ),
            Distributor(id="cdn_distributor", type_id="docker_rsync_distributor"),
            Distributor(
                id="cdn_distributor_unprotected", type_id="docker_rsync_distributor"
            ),
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
            {"json": [{"task_id": "task2", "state": "finished"}]},
            {"json": [{"task_id": "task3", "state": "finished"}]},
        ],
    )

    # It should have succeeded, with the tasks as retrieved from Pulp
    assert sorted(repo.publish()) == [
        Task(id="task1", succeeded=True, completed=True),
        Task(id="task2", succeeded=True, completed=True),
        Task(id="task3", succeeded=True, completed=True),
    ]

    req = requests_mocker.request_history
    ids = [r.json()["id"] for r in req if r.url.endswith("/publish/")]

    # It should have triggered these distributors in this order
    assert ids == [
        "cdn_distributor",
        "cdn_distributor_unprotected",
        "docker_web_distributor_name_cli",
    ]


def test_publish_origin_only(requests_mocker, client):
    """publish skips docker distributor if origin_only=True"""
    repo = ContainerImageRepository(
        id="some-repo",
        distributors=(
            Distributor(
                id="docker_web_distributor_name_cli", type_id="docker_distributor_web"
            ),
            Distributor(id="cdn_distributor", type_id="docker_rsync_distributor"),
            Distributor(
                id="cdn_distributor_unprotected", type_id="docker_rsync_distributor"
            ),
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

    # It should have succeeded, with the tasks as retrieved from Pulp
    assert sorted(repo.publish(PublishOptions(origin_only=True))) == [
        Task(id="task1", succeeded=True, completed=True),
        Task(id="task2", succeeded=True, completed=True),
    ]

    req = requests_mocker.request_history
    publish_req = [r for r in req if r.url.endswith("/publish/")]

    # It should have triggered these distributors in this order
    ids = [r.json()["id"] for r in publish_req]
    assert ids == ["cdn_distributor", "cdn_distributor_unprotected"]

    # It should have triggered with content_units_only=True
    assert publish_req[-1].json()["override_config"]["content_units_only"]
