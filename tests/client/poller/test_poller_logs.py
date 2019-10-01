import logging

import requests
import mock

from pubtools.pulplib._impl.client.poller import TaskPoller


def test_logs_task_completion(requests_mocker, caplog):
    """Poller logs tasks as they complete."""
    caplog.set_level(logging.INFO)

    poller = TaskPoller(requests.Session(), "https://pulp.example.com/")

    desc_completed = mock.Mock()
    desc_completed.result = {"spawned_tasks": [{"task_id": "completed-task"}]}

    desc_failed = mock.Mock()
    desc_failed.result = {"spawned_tasks": [{"task_id": "failed-task"}]}

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        json=[
            {
                "task_id": "completed-task",
                "state": "finished",
                "tags": ["pulp:tag1", "pulp:tag2", "other-tag"],
            },
            {
                "task_id": "failed-task",
                "state": "error",
                "tags": [
                    "pulp:repository:all-rpm-content",
                    "pulp:action:import_upload",
                ],
            },
        ],
    )

    descriptors = [desc_completed, desc_failed]

    poller(descriptors)

    logs = [(rec.levelno, rec.message) for rec in caplog.records]

    # It should have logged about the completed tasks.
    assert sorted(logs) == [
        (logging.INFO, "Pulp task completed: completed-task, tag1, tag2, other-tag"),
        (
            logging.WARNING,
            "Pulp task failed: failed-task, repository:all-rpm-content, action:import_upload",
        ),
    ]
