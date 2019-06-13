import pytest
import requests_mock
from pubtools.pulplib import Client, Criteria, Repository, PulpException

from more_executors.retry import ExceptionRetryPolicy


def test_can_construct(requests_mocker):
    client = Client("https://pulp.example.com/")


def test_can_construct_with_session_args(requests_mocker):
    client = Client("https://pulp.example.com/", auth=("x", "y"), verify=False)


def test_construct_raises_on_bad_args(requests_mocker):
    with pytest.raises(TypeError):
        client = Client("https://pulp.example.com/", whatever="foobar")


def test_search_raises_on_bad_args(client, requests_mocker):
    with pytest.raises(TypeError):
        client.search_repository("oops, not valid criteria")


def test_can_search(client, requests_mocker):
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


def test_search_retries(client, requests_mocker):
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


def test_search_can_paginate(client, requests_mocker):
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
    assert "repo1 was not found" in str(error)
