import time
from pubtools.pulplib import Repository


def test_search_stops_paginate(client, requests_mocker):
    """Paginated search will stop issuing requests if pages are no longer referenced."""

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

    # Imagine we have some function which processes two pages of results and
    # then stops
    def do_something_first_two_pages(repos_f):
        page = repos_f.result()
        return len(page.data) + len(page.next.result().data)

    two_pages_len = do_something_first_two_pages(client.search_repository())

    # It should have seen the first two pages
    assert two_pages_len == 20

    # Now wait a bit to ensure any futures under the hood have time to finish up
    time.sleep(2.0)

    # It should have done only two or three requests
    # (2 vs 3 depends on scheduling). Because we threw away all references to
    # the search result, it stopped searching rather than continuing through
    # all pages.
    assert requests_mocker.call_count in (2, 3)
