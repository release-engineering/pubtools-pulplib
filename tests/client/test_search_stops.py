import time
from pubtools.pulplib import Client


def test_search_stops_paginate(requests_mocker):
    """Paginated search will stop issuing requests if pages are no longer referenced."""

    client = Client("https://pulp.example.com/")
    client._PAGE_SIZE = 10

    responses = []
    current_response = []
    for i in range(0, 997):
        repo_id = "repo-%s" % i
        current_response.append({"id": repo_id})
        if len(current_response) == client._PAGE_SIZE:
            responses.append({"json": current_response})
            current_response = []

    responses.append({"json": current_response})

    # Inject a failing response for stable behavior from test:
    #
    # The expected behavior is that, after the first two requests,
    # pagination is cancelled since we no longer hold onto a page.
    # But that cancellation is racing with the scheduling of the
    # request, and there is generally no way to ensure our cancel
    # happens before the request thread starts the request, so we
    # can't be sure about how many requests we'd do.
    #
    # However, if we insert a failure after the first two pages,
    # then the client will need to retry a request (with some delay).
    # It should always be possible to cancel the request during that
    # retry delay, making the test stable.
    responses.insert(2, {"status_code": 500})

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/", responses
    )

    # Imagine we have some function which processes two pages of results and
    # then stops
    def do_something_first_two_pages(page):
        return len(page.data) + len(page.next.data)

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
