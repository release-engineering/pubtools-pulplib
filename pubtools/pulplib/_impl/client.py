from .criteria import Criteria


class Client(object):
    """A client for the Pulp 2.x API.

    This class provides high-level methods for querying a Pulp server and performing
    actions in Pulp.

    **Usage of futures:**

    Most values are returned as :class:`~concurrent.futures.Future` objects.
    Returned futures are resolved when:

    - a request to Pulp succeeded, if operation is synchronous (e.g. get, search)
    - or a request to Pulp succeeded and any spawned tasks succeeded, if operation
      is asynchronous (e.g. publish)

    **Retries:**

    In general, for all methods which represent an idempotent operation and
    which return a Future, the library may retry operations several times in case
    of failure.

    **Throttling:**

    This client will internally throttle the number of Pulp tasks allowed to be
    outstanding at any given time, so that no single client can overload the Pulp
    task queue.
    """

    # TODO: customization of retry & throttling logic.
    # Should the class expose anything for those, or keep all policy internal?

    def __init__(self, url, **kwargs):
        """
        Args:
            str url
                URL of a Pulp server, e.g. https://pulp.example.com/.

            object auth, cert, headers, max_redirects, params, proxies, verify
                Any of these arguments, if provided, are used to initialize
                :class:`requests.Session` objects used by the client.

                These may be used, for example, to configure the credentials
                for the Pulp server or to use an alternative CA bundle.
        """

    def search_repository(self, criteria):
        """Search for repositories matching the given criteria.

        Args:
            criteria (:class:`~pubtools.pulplib.Criteria`)
                A criteria object used for this search.

        Returns:
            Future[:class:`~pubtools.pulplib.Page`]
                A future representing the first page of results.

                Each page will contain a collection of
                :class:`~pubtools.pulplib.Repository` objects.
        """

    def get_repository(self, id):
        """Get a repository by ID.

        Args:
            id (str)
                The ID of the repository to be fetched.

        Returns:
            Future[:class:`~pubtools.pulplib.Repository`]
                A future holding the fetched Repository.
        """
        # sketch of possible implementation (reuse search)
        page_f = self.search_repository(Criteria.with_ids(id))
        repo_f = f_map(page_f, lambda page: page.data[0])
        return repo_f


# Design notes
# ============
#
# This library aims to fully enable both non-blocking and blocking coding styles,
# so that callers can pipeline as much as possible (if they need best possible
# performance and are willing to pay the complexity for that), or can write code
# in simpler blocking style if they don't care much.
#
# As such, futures are used for almost everything, because they can be chained
# to remain non-blocking as long as the caller wants, or have .result() called to
# immediately block on any result.
#
# The set of operations available in the client is minimal - we're only implementing
# what we need, as we need it.
#
