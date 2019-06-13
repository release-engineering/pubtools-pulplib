import logging
import datetime
import requests
import mock

from pubtools.pulplib._impl.client.poller import TaskPoller


class Timer(object):
    def __init__(self, delta):
        self.next_time = datetime.datetime.utcnow()
        self.delta = delta

    def increment(self):
        self.next_time = self.next_time + self.delta

    def __call__(self):
        return self.next_time


def test_logs_if_inactive(requests_mocker, caplog):
    """Poller produces log messages showing Pulp's load if it seems inactive"""

    caplog.set_level(logging.INFO, "pubtools.pulplib")

    descriptor = mock.Mock()
    descriptor.result = {"spawned_tasks": [{"task_id": "some-task"}]}

    timer = Timer(datetime.timedelta(minutes=1))

    poller = TaskPoller(requests.Session(), "https://pulp.example.com/", timer)
    poller.ACTIVITY_DELAY = datetime.timedelta(minutes=4)

    def searching_on_id(request):
        return "task_id" in request.json().get("criteria", {}).get("filters", {})

    search_url = "https://pulp.example.com/pulp/api/v2/tasks/search/"

    # When poller searches for task ID, it finds it
    requests_mocker.post(
        search_url,
        additional_matcher=searching_on_id,
        json=[{"task_id": "some-task", "state": "waiting"}],
    )

    # When poller searches for task states, it gets many tasks
    requests_mocker.post(
        search_url,
        additional_matcher=lambda req: not searching_on_id(req),
        json=[{"state": "waiting"}] * 3 + [{"state": "running"}] * 5,
    )

    # Let's poll a few times
    poller([descriptor])
    timer.increment()
    poller([descriptor])
    timer.increment()
    poller([descriptor])
    timer.increment()

    # Descriptor hasn't been updated...
    descriptor.yield_result.assert_not_called()
    descriptor.yield_exception.assert_not_called()

    # But shouldn't have logged anything yet
    assert caplog.messages == []

    # But now if we allow more time to pass...
    timer.increment()
    timer.increment()

    # And try to poll again
    poller([descriptor])

    # Now it should have logged a message
    assert caplog.messages == ["Still waiting on Pulp, load: 5 running, 3 waiting"]

    caplog.clear()

    # If we poll again soon...
    timer.increment()
    poller([descriptor])

    # It shouldn't repeat the message so soon
    assert caplog.messages == []

    # But if we keep going, the log message will repeat every few minutes
    timer.increment()
    timer.increment()
    timer.increment()
    poller([descriptor])
    assert caplog.messages == ["Still waiting on Pulp, load: 5 running, 3 waiting"]

    # And the records should contain our documented 'extra'
    record = caplog.records[0]
    assert record.event == {
        "type": "awaiting-pulp",
        "running-tasks": 5,
        "waiting-tasks": 3,
    }
