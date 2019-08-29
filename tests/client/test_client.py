import logging
import pytest
import requests_mock
from pubtools.pulplib import Client, Criteria, Repository, PulpException, Distributor


def test_can_construct(requests_mocker):
    """A client instance can be constructed with URL alone."""
    client = Client("https://pulp.example.com/")


def test_can_construct_with_session_args(requests_mocker):
    """A client instance can be constructed with requests.Session kwargs."""
    client = Client("https://pulp.example.com/", auth=("x", "y"), verify=False)


def test_construct_raises_on_bad_args(requests_mocker):
    """A client instance cannot be constructed with unexpected args."""
    with pytest.raises(TypeError):
        client = Client("https://pulp.example.com/", whatever="foobar")


def test_search_raises_on_bad_args(client, requests_mocker):
    """search_repository raises TypeError if passed something other than Criteria"""
    with pytest.raises(TypeError):
        client.search_repository("oops, not valid criteria")


def test_can_search(client, requests_mocker):
    """search_repository issues /search/ POST requests as expected."""
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/",
        json=[{"id": "repo1"}, {"id": "repo2"}],
    )

    repos_f = client.search_repository()

    repos = [r for r in repos_f.result().as_iter()]

    # It should have returned the repos as objects
    assert sorted(repos) == [Repository(id="repo1"), Repository(id="repo2")]

    # It should have issued only a single search
    assert requests_mocker.call_count == 1


def test_can_search_distributor(client, requests_mocker):
    """search_distributor issues distributors/search POST request as expected."""
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/distributors/search/",
        json=[{"id": "yum_distributor", "distributor_type_id": "yum_distributor", "repo_id": "test_rpm"},
              {"id": "cdn_distributor", "distributor_type_id": "rpm_rsync_distributor"}
        ]
    )

    distributors_f = client.search_distributor()
    distributors = [dist for dist in distributors_f.result().as_iter()]
    # distributor objects are returned
    assert sorted(distributors) == [Distributor(id="cdn_distributor", type_id="rpm_rsync_distributor"), Distributor(id="yum_distributor", type_id="yum_distributor", repo_id="test_rpm")]
    # api is called once
    assert requests_mocker.call_count == 1


def test_search_retries(client, requests_mocker, caplog):
    """search_repository retries operations on failure."""
    logging.getLogger().setLevel(logging.WARNING)
    caplog.set_level(logging.WARNING)

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/",
        [
            {"status_code": 413},
            {"status_code": 500},
            # Let's also mix in something which isn't valid json
            {"text": '{"not-valid-json": '},
            {"json": [{"id": "repo1"}]},
        ],
    )

    repos_f = client.search_repository()

    repos = [r for r in repos_f.result().as_iter()]

    # It should have found the repo
    assert repos == [Repository(id="repo1")]

    # But would have needed several attempts
    assert requests_mocker.call_count == 4

    # And those retries should have been logged
    messages = caplog.messages
    assert len(messages) == 3

    # Messages have full exception detail. Just check the first line.
    lines = [m.splitlines()[0] for m in messages]

    assert lines[0].startswith("Retrying due to error: 413")
    assert lines[0].endswith(" [1/6]")
    assert lines[1].startswith("Retrying due to error: 500")
    assert lines[1].endswith(" [2/6]")
    assert lines[2].startswith("Retrying due to error:")
    assert lines[2].endswith(" [3/6]")

    # Retry logs should have the pulp-retry event attached.
    assert caplog.records[-1].event == {"type": "pulp-retry"}


def test_search_can_paginate(client, requests_mocker):
    """search_repository implicitly paginates the search as needed."""
    client._PAGE_SIZE = 10

    expected_repos = []
    responses = []
    current_response = []
    for i in range(0, 997):
        repo_id = "repo-%s" % i
        expected_repos.append(Repository(id=repo_id))
        current_response.append({"id": repo_id})
        if len(current_response) == client._PAGE_SIZE:
            responses.append({"json": current_response})
            current_response = []

    responses.append({"json": current_response})

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/", responses
    )

    repos_f = client.search_repository()

    repos = [r for r in repos_f.result().as_iter()]

    # It should have returned the repos as objects
    assert sorted(repos) == sorted(expected_repos)

    # It needed to do 100 requests to get all the data
    assert requests_mocker.call_count == 100

    # Requests should have used skip/limit to paginate appropriately.
    # We'll just sample a few of the requests here.
    history = requests_mocker.request_history
    criteria = [h.json()["criteria"] for h in history]
    assert criteria[0] == {"filters": {}, "skip": 0, "limit": 10}
    assert criteria[1] == {"filters": {}, "skip": 10, "limit": 10}
    assert criteria[2] == {"filters": {}, "skip": 20, "limit": 10}
    assert criteria[-1] == {"filters": {}, "skip": 990, "limit": 10}


def test_can_get(client, requests_mocker):
    """get_repository gets a repository (via search)."""
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/",
        json=[{"id": "repo1"}],
    )

    repo_f = client.get_repository("repo1")

    # It should have returned the expected repo
    assert repo_f.result() == Repository(id="repo1")

    # It should have issued only a single search
    assert requests_mocker.call_count == 1

    # The search should have used these filters
    assert requests_mocker.last_request.json()["criteria"].get("filters") == {
        "id": {"$eq": "repo1"}
    }


def test_get_missing(client, requests_mocker):
    """get_repository raises meaningful exception if repo is missing"""

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/", json=[]
    )

    repo_f = client.get_repository("repo1")

    # It should raise
    with pytest.raises(PulpException) as error:
        repo_f.result()

    # It should explain the problem
    assert "repo1 was not found" in str(error.value)
