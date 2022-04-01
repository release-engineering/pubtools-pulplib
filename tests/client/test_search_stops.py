import time
import gc

from more_executors.futures import f_flat_map, f_return

from pubtools.pulplib import Client


def test_search_stops_paginate(requests_mocker):
    """Paginated search will stop issuing requests if pages are no longer referenced."""

    with Client("https://pulp.example.com/") as client:
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
        time.sleep(5.0)

        # It should have done only two or three requests
        # (2 vs 3 depends on scheduling). Because we threw away all references to
        # the search result, it stopped searching rather than continuing through
        # all pages.
        assert requests_mocker.call_count in (2, 3)


def test_search_async_cb(requests_mocker):
    """Paginated search works fine with an async callback on page.next.

    This test aims to cover a specific bug by which searches may be incorrectly
    cancelled even if the result was being awaited.
    """

    with Client("https://pulp.example.com/") as client:
        client._PAGE_SIZE = 10

        class ResponseGenerator(object):
            def __init__(self):
                self.repo_ids = ["repo-%s" % i for i in range(0, 997)]

            def __call__(self, request, context):
                # We're trying to trigger a certain bug which happens depending
                # on timing of GC. Simulating a non-instant HTTP request helps to
                # trigger it reliably.
                time.sleep(0.01)

                current_response = []
                while self.repo_ids:
                    current_response.append({"id": self.repo_ids.pop(0)})
                    if len(current_response) == client._PAGE_SIZE:
                        break

                # GC in the middle of HTTP requests to increase chance of
                # hitting the error scenario.
                gc.collect()

                return current_response

        requests_mocker.post(
            "https://pulp.example.com/pulp/api/v2/repositories/search/",
            json=ResponseGenerator(),
        )

        class Handler(object):
            def __init__(self):
                self._got_data = []

            def __call__(self, page):
                self._got_data.extend(page.data)
                if page.next:
                    # set ourselves up to process the next page.
                    # It's important here that we only grab a reference to page.next
                    # and don't keep a reference to page, as we are trying to cover
                    # a previous bug where that scenario would wrongly cancel search.
                    return f_flat_map(page.next, self)
                return f_return(self._got_data)

        all_data_f = f_flat_map(client.search_repository(), Handler())

        # Searches are now running. Let's try doing many GCs while that's in progress
        # to increase the chance that we'll trigger the targeted bug.
        for _ in range(0, 50):
            gc.collect()

        # It should be able to complete the search.
        # Note: if "early GC" bug is not fixed, it would hang here, hence the
        # application of a timeout.
        all_data = all_data_f.result(10.0)

        # It should get all the repos successfully.
        ids = [repo.id for repo in all_data]
        assert ids == ["repo-%s" % i for i in range(0, 997)]
