import json
import logging

from pubtools.pulplib import FileRepository, Task, Distributor


def test_publish_update_mappings(fast_poller, requests_mocker, client, caplog):
    """Publish on FileRepository will generate ud_file_release_mappings_2."""

    caplog.set_level(logging.INFO, "pubtools.pulplib")

    repo = FileRepository(
        id="some-repo",
        distributors=[Distributor(id="iso_distributor", type_id="iso_distributor")],
    )
    repo.__dict__["_client"] = client

    # Force client to use a small page size so that we're able to verify
    # all pages end up handled.
    client._PAGE_SIZE = 3

    # Arrange for the repo to currently exist with some mappings.
    requests_mocker.get(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/",
        json={
            "id": "some-repo",
            "notes": {
                "ud_file_release_mappings_2": json.dumps(
                    # Define some mappings so there's a mix of data needing
                    # an update and data needing no update.
                    {
                        "1.0": [{"filename": "file1", "order": 3.0}],
                        "3.0": [{"filename": "file3", "order": 1234}],
                        "4.0": [{"filename": "file4", "order": 0}],
                        "some-other-version": [
                            {"filename": "whatever-file", "order": "abc", "foo": "bar"}
                        ],
                    }
                )
            },
        },
    )

    # Make the repo have some units with the mapping-relevant fields. We use
    # two pages here to ensure that the code implements pagination.
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        [
            {
                # page 1
                "json": [
                    {
                        "metadata": {
                            "_content_type_id": "iso",
                            "name": "file1",
                            "size": 1,
                            "checksum": "cd293be6cea034bd45a0352775a219ef5dc7825ce55d1f7dae9762d80ce64411",
                            "pulp_user_metadata": {
                                "version": "1.0",
                                "display_order": 3.0,
                            },
                        }
                    },
                    {
                        "metadata": {
                            "_content_type_id": "iso",
                            "name": "file2",
                            "size": 1,
                            "checksum": "cd293be6cea034bd45a0352775a219ef5dc7825ce55d1f7dae9762d80ce64411",
                        }
                    },
                    {
                        "metadata": {
                            "_content_type_id": "iso",
                            "name": "file3",
                            "size": 1,
                            "checksum": "cd293be6cea034bd45a0352775a219ef5dc7825ce55d1f7dae9762d80ce64411",
                            "pulp_user_metadata": {"version": "3.0"},
                        }
                    },
                ]
            },
            {
                # page 2
                "json": [
                    {
                        "metadata": {
                            "_content_type_id": "iso",
                            "name": "file4",
                            "size": 1,
                            "checksum": "cd293be6cea034bd45a0352775a219ef5dc7825ce55d1f7dae9762d80ce64411",
                            "pulp_user_metadata": {
                                "version": "4.0",
                                "display_order": -2,
                            },
                        }
                    },
                    {
                        "metadata": {
                            "_content_type_id": "iso",
                            "name": "file5",
                            "size": 1,
                            "checksum": "cd293be6cea034bd45a0352775a219ef5dc7825ce55d1f7dae9762d80ce64411",
                            "pulp_user_metadata": {
                                "version": "1.0",
                                "display_order": 4.5,
                            },
                        }
                    },
                    {
                        "metadata": {
                            "_content_type_id": "iso",
                            "name": "file6",
                            "size": 1,
                            "checksum": "cd293be6cea034bd45a0352775a219ef5dc7825ce55d1f7dae9762d80ce64411",
                            "pulp_user_metadata": {"version": "6.0"},
                        }
                    },
                ]
            },
            {
                # page 3: nothing more
                "json": []
            },
        ],
    )

    # Allow for an update to the repository.
    requests_mocker.put(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/", json={}
    )

    # It should publish as usual.
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/publish/",
        json={"spawned_tasks": [{"task_id": "publish-task"}]},
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        json=[{"task_id": "publish-task", "state": "finished"}],
    )

    # It should have succeeded, with the publish task as retrieved from pulp
    assert sorted(repo.publish()) == [
        Task(id="publish-task", succeeded=True, completed=True)
    ]

    # Now let's have a look at what it updated.
    # The last operations are (update repo, start publish, await tasks),
    # so the update request should always be the 3rd last.
    req = requests_mocker.request_history[-3]

    # Should have been a PUT to the repo.
    assert req.url == "https://pulp.example.com/pulp/api/v2/repositories/some-repo/"
    assert req.method == "PUT"

    # It should have included this field in the delta...
    mapping_json = req.json()["delta"]["notes"]["ud_file_release_mappings_2"]

    # It should have been valid JSON
    mapping = json.loads(mapping_json)

    # It should be equal to this:
    assert mapping == {
        "1.0": [
            # This file wasn't changed
            {"filename": "file1", "order": 3.0},
            # This was added
            {"filename": "file5", "order": 4.5},
        ],
        # This wasn't touched because, although the repo has the file, it has no
        # defined order
        "3.0": [{"filename": "file3", "order": 1234}],
        # This was updated
        "4.0": [{"filename": "file4", "order": -2.0}],
        # This was added, with the entire version not previously defined.
        # Also, order field is omitted because none was in the data, but
        # the version and file still must be written.
        "6.0": [{"filename": "file6"}],
        # This is some unrelated junk which should be left alone during the
        # update process.
        "some-other-version": [
            {"filename": "whatever-file", "foo": "bar", "order": "abc"}
        ],
    }

    # It should have logged that this happened
    assert "Updated ud_file_release_mappings_2 in some-repo" in caplog.messages


def test_publish_update_mappings_noop(fast_poller, requests_mocker, client):
    """Publish on FileRepository does not do unnecessary repo updates."""
    repo = FileRepository(
        id="some-repo",
        distributors=[Distributor(id="iso_distributor", type_id="iso_distributor")],
    )
    repo.__dict__["_client"] = client

    # Arrange for the repo to currently exist with up-to-date mappings.
    requests_mocker.get(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/",
        json={
            "id": "some-repo",
            "notes": {
                "ud_file_release_mappings_2": json.dumps(
                    {
                        "1.0": [
                            {"filename": "file1", "order": 3.0},
                            {"filename": "file2", "order": 6.0},
                        ],
                        "other": ["whatever"],
                    }
                )
            },
        },
    )

    # Make the repo have some units with the mapping-relevant fields.
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=[
            {
                "metadata": {
                    "_content_type_id": "iso",
                    "name": "file1",
                    "size": 1,
                    "checksum": "cd293be6cea034bd45a0352775a219ef5dc7825ce55d1f7dae9762d80ce64411",
                    "pulp_user_metadata": {"version": "1.0", "display_order": 3.0},
                }
            },
            {
                "metadata": {
                    "_content_type_id": "iso",
                    "name": "file2",
                    "size": 1,
                    "checksum": "cd293be6cea034bd45a0352775a219ef5dc7825ce55d1f7dae9762d80ce64411",
                    "pulp_user_metadata": {"version": "1.0"},
                }
            },
        ],
    )

    # It should NOT update the repository, so we don't register any PUT.

    # It should publish as usual.
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/actions/publish/",
        json={"spawned_tasks": [{"task_id": "publish-task"}]},
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        json=[{"task_id": "publish-task", "state": "finished"}],
    )

    # It should have succeeded, with the tasks as retrieved from Pulp
    assert sorted(repo.publish()) == [
        Task(id="publish-task", succeeded=True, completed=True)
    ]
