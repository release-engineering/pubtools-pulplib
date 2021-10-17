from pubtools.pulplib import Repository, Task, RpmUnit, ModulemdUnit, Criteria, Matcher


def test_copy_no_criteria(fast_poller, requests_mocker, client):
    """Copy succeeds when given no criteria"""

    src = Repository(id="src-repo")
    dest = Repository(id="dest-repo")

    src.__dict__["_client"] = client
    dest.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/dest-repo/actions/associate/",
        [{"json": {"spawned_tasks": [{"task_id": "task1"}, {"task_id": "task2"}]}}],
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        [
            {
                "json": [
                    {
                        "task_id": "task1",
                        "state": "finished",
                        "result": {
                            "units_successful": [
                                {
                                    "type_id": "modulemd",
                                    "unit_key": {
                                        "name": "module",
                                        "stream": "s1",
                                        "version": 1234,
                                        "context": "a1b2c3",
                                        "arch": "s390x",
                                    },
                                }
                            ]
                        },
                    },
                    {"task_id": "task2", "state": "skipped"},
                ]
            }
        ],
    )

    # Copy should succeed, and return the tasks with units parsed.
    assert sorted(client.copy_content(src, dest), key=lambda t: t.id) == [
        Task(
            id="task1",
            completed=True,
            succeeded=True,
            units=[
                ModulemdUnit(
                    name="module",
                    stream="s1",
                    version=1234,
                    context="a1b2c3",
                    arch="s390x",
                    content_type_id="modulemd",
                )
            ],
            units_data=[
                {
                    "type_id": "modulemd",
                    "unit_key": {
                        "name": "module",
                        "stream": "s1",
                        "version": 1234,
                        "context": "a1b2c3",
                        "arch": "s390x",
                    },
                }
            ],
        ),
        Task(id="task2", completed=True, succeeded=True),
    ]

    hist = requests_mocker.request_history

    # First request should have been the associate.
    assert (
        hist[0].url
        == "https://pulp.example.com/pulp/api/v2/repositories/dest-repo/actions/associate/"
    )

    # It should have posted for the given source repo, with empty criteria.
    assert hist[0].json() == {"criteria": {}, "source_repo_id": "src-repo"}


def test_copy_with_criteria(fast_poller, requests_mocker, client):
    """Copy with criteria succeeds, and serializes criteria correctly."""

    src = Repository(id="src-repo")
    dest = Repository(id="dest-repo")

    src.__dict__["_client"] = client
    dest.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/dest-repo/actions/associate/",
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

    crit = Criteria.and_(
        Criteria.with_unit_type(RpmUnit),
        Criteria.with_field("name", Matcher.in_(["bash", "glibc"])),
    )

    # Copy should succeed, and return the tasks (in this case with no matches)
    assert sorted(client.copy_content(src, dest, crit), key=lambda t: t.id) == [
        Task(id="task1", completed=True, succeeded=True),
        Task(id="task2", completed=True, succeeded=True),
    ]

    hist = requests_mocker.request_history

    # First request should have been the associate.
    assert (
        hist[0].url
        == "https://pulp.example.com/pulp/api/v2/repositories/dest-repo/actions/associate/"
    )

    # It should have encoded our criteria object as needed by the Pulp API.
    assert hist[0].json() == {
        "criteria": {
            "filters": {"unit": {"name": {"$in": ["bash", "glibc"]}}},
            "type_ids": ["rpm", "srpm"],
        },
        "source_repo_id": "src-repo",
    }
