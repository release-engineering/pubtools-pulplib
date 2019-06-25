import time

from pubtools.pulplib import YumRepository, Distributor


def test_publish_cancel(fast_poller, requests_mocker, client, caplog):
    """Cancelling a publish future will cancel running Pulp task(s)."""

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
        [{"json": {"spawned_tasks": [{"task_id": "task1"}]}}],
    )

    task_search_url = "https://pulp.example.com/pulp/api/v2/tasks/search/"
    requests_mocker.post(
        task_search_url, [{"json": [{"task_id": "task1", "state": "running"}]}]
    )

    requests_mocker.delete("https://pulp.example.com/pulp/api/v2/tasks/task1/")

    # Start the publish
    publish_f = repo.publish()

    # Wait until we're sure poll thread has seen this task
    for _ in range(0, 1000):
        if (
            requests_mocker.last_request
            and requests_mocker.last_request.url == task_search_url
        ):
            break
        time.sleep(0.001)
    assert requests_mocker.last_request.url == task_search_url

    # We should be able to cancel it
    assert publish_f.cancel()

    # It should have cancelled the underlying Pulp task
    task_req = [
        r
        for r in requests_mocker.request_history
        if r.url == "https://pulp.example.com/pulp/api/v2/tasks/task1/"
    ]
    assert len(task_req) == 1
    assert task_req[0].method == "DELETE"
