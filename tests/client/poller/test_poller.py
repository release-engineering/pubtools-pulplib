import requests
import mock
import pytest

from pubtools.pulplib import Task, TaskFailedException
from pubtools.pulplib._impl.client.poller import TaskPoller
from pubtools.pulplib._impl.client.errors import MissingTaskException


def test_does_nothing_with_no_descriptors(requests_mocker):
    """TaskPoller doesn't do anything if there's no descriptors to poll."""
    poller = TaskPoller(requests.Session(), "https://pulp.example.com/")

    # It should run successfully
    delay = poller([])

    # It should not have made any requests
    assert requests_mocker.call_count == 0

    # It should request next poll at default interval
    assert delay == poller.DELAY


def test_mixed_tasks(requests_mocker):
    """Poller correctly handles a set of descriptors with tasks in different states."""
    poller = TaskPoller(requests.Session(), "https://pulp.example.com/")

    desc_completed = mock.Mock()
    desc_completed.result = {"spawned_tasks": [{"task_id": "completed-task"}]}

    desc_completed_later = mock.Mock()
    desc_completed_later.result = {
        "spawned_tasks": [{"task_id": "completed-later-task"}]
    }

    desc_failed = mock.Mock()
    desc_failed.result = {"spawned_tasks": [{"task_id": "failed-task"}]}

    desc_missing = mock.Mock()
    desc_missing.result = {"spawned_tasks": [{"task_id": "missing-task"}]}

    desc_invalid = mock.Mock()
    desc_invalid.result = {"spawned_tasks": "some garbage!"}

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        [
            # First response
            dict(
                json=[
                    {"task_id": "completed-task", "state": "finished"},
                    {"task_id": "failed-task", "state": "error"},
                    # completed-later task is still in progress
                    {"task_id": "completed-later-task", "state": "running"},
                    # no entry for missing-task
                ]
            ),
            # Second response only covers the task expected to be queried at second poll
            dict(json=[{"task_id": "completed-later-task", "state": "finished"}]),
        ],
    )

    descriptors = [
        desc_completed,
        desc_completed_later,
        desc_failed,
        desc_invalid,
        desc_missing,
    ]

    # First poll: attempt to process all descriptors.
    # Poll function should complete successfully.
    poller(descriptors)

    # This descriptor should have yielded a Task result
    desc_completed.yield_result.assert_called_once_with(
        [Task(id="completed-task", completed=True, succeeded=True)]
    )

    # This one hasn't yielded anything yet
    desc_completed_later.yield_result.assert_not_called()
    desc_completed_later.yield_exception.assert_not_called()

    # This one has yielded an exception since the task failed
    assert len(desc_failed.yield_exception.mock_calls) == 1
    exception = desc_failed.yield_exception.mock_calls[0][1][0]
    assert isinstance(exception, TaskFailedException)
    assert exception.task.id == "failed-task"

    # This one has yielded an (undefined) exception since the result couldn't
    # even be matched up with a task ID
    assert len(desc_invalid.yield_exception.mock_calls) == 1
    exception = desc_invalid.yield_exception.mock_calls[0][1][0]
    # (we are not guaranteeing anything about the exception raised in this case,
    # this just happens to be the message generated for the exception raised by
    # the particular invalid data we prepared)
    assert "string indices must be integers" in str(exception)

    # This one has yielded a MissingTaskException since the task ID we were
    # looking for wasn't returned by a search
    assert len(desc_missing.yield_exception.mock_calls) == 1
    exception = desc_missing.yield_exception.mock_calls[0][1][0]
    assert isinstance(exception, MissingTaskException)
    assert "missing-task disappeared from Pulp" in str(exception)

    # Second poll: should find that completed-task is now done
    poller([desc_completed_later])

    # Now it should have yielded a Task result
    desc_completed_later.yield_result.assert_called_once_with(
        [Task(id="completed-later-task", completed=True, succeeded=True)]
    )

    # For all descriptors, yield_result OR yield_exception should have been called,
    # but not both
    for desc in descriptors:
        assert 1 == desc.yield_result.call_count + desc.yield_exception.call_count


def test_retries(requests_mocker):
    """Poller retries failing task searches to Pulp"""
    poller = TaskPoller(requests.Session(), "https://pulp.example.com/")

    desc = mock.Mock()
    desc.result = {"spawned_tasks": [{"task_id": "task1"}]}

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        [
            # First response fails
            dict(status_code=400),
            # Second response fails again in an odd way (truncated JSON)
            dict(headers={"Content-Type": "application/json"}, text='["not valid!'),
            # Finally works at the third response
            dict(json=[{"task_id": "task1", "state": "finished"}]),
        ],
    )

    # First poll doesn't touch descriptor
    poller([desc])
    desc.yield_result.assert_not_called()
    desc.yield_exception.assert_not_called()

    # Second poll doesn't touch descriptor
    poller([desc])
    desc.yield_result.assert_not_called()
    desc.yield_exception.assert_not_called()

    # Third poll finally succeeds
    poller([desc])
    desc.yield_result.assert_called_once_with(
        [Task(id="task1", completed=True, succeeded=True)]
    )
    desc.yield_exception.assert_not_called()


def test_retries_exhausted(requests_mocker):
    """Poller eventually raises if retries are exhausted"""
    poller = TaskPoller(requests.Session(), "https://pulp.example.com/")
    poller.MAX_ATTEMPTS = 5

    desc1 = mock.Mock()
    desc1.result = {"spawned_tasks": [{"task_id": "task1"}]}
    desc2 = mock.Mock()
    desc2.result = {"spawned_tasks": [{"task_id": "task2"}]}
    descriptors = [desc1, desc2]

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/", status_code=400
    )

    # First poll fails but descriptors aren't marked failed yet...
    for _ in range(0, poller.MAX_ATTEMPTS - 1):
        poller(descriptors)
        # Not the last poll yet, so descriptors aren't marked as failed yet...
        for desc in descriptors:
            desc.yield_result.assert_not_called()
            desc.yield_exception.assert_not_called()

    # But if we poll one last time, it'll finally allow the exception to propagate
    with pytest.raises(Exception) as exc_info:
        poller(descriptors)

    # It should pass through whatever was the underlying error
    assert "400 Client Error" in str(exc_info.value)
