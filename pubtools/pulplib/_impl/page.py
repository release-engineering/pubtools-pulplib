import logging
import weakref

from . import compat_attr as attr

LOG = logging.getLogger("pubtools.pulplib")


@attr.s(kw_only=True)
class Page(object):
    """A page of Pulp search results.

    All Pulp searches issued by this library are paginated.
    Instances of this class may be used to iterate through the returned
    pages, in both blocking and non-blocking coding styles.

    Examples:

        **Non-blocking iteration**

        This example sets up non-blocking processing of all results from
        a search query. Futures are chained and composed using
        :func:`~more_executors.futures.f_flat_map` and friends.

        .. code-block:: python

            def handle_results(page):
                # Returns a future for handling of a single page
                for repo in page.data:
                    do_something(repo)
                if page.next:
                    # There's more data, handle that too when it's ready
                    return f_flat_map(page.next, handle_results)
                # No more data, we're done
                print("Handled results!")
                return f_return()

            page_f = client.search_repository(...)
            handled_f = f_flat_map(page_f, handle_results)
            # handled_f will be resolved when all results are handled

        **Blocking iteration**

        This example uses :meth:`as_iter` to loop over all search results.
        At certain points during the iteration, blocking may occur to
        await more pages from Pulp.

        .. code-block:: python

            page = client.search_repository(...).result()
            # processes all data, but may block at page boundaries
            for repo in page.as_iter():
                do_something(repo)

    """

    data = attr.ib(default=attr.Factory(list))
    """List of Pulp objects in this page.

    This list will contain instances of the appropriate Pulp object type
    (e.g. :class:`~pubtools.pulplib.Repository` for a repository search).
    """

    next = attr.ib(default=None)
    """None, if this is the last page of results.

    Otherwise, a Future[:class:`Page`] for the next page of results.
    """

    def __attrs_post_init__(self):
        if self.next:
            # If *this* page disappears, it's pointless to keep querying for
            # the next page, so we could cancel that future.
            #
            # Note: when we are Py3-only, this could be better rewritten
            # using weakref.finalize or even just plain __del__

            to_cancel = self.next

            def do_cancel(*_):
                if not to_cancel.done():
                    cancel_result = to_cancel.cancel()
                    LOG.debug("Cancel next page due to GC: %s", cancel_result)

            # Just stash a weakref anywhere it'll stay alive for as long
            # as the page itself.
            self.__dict__["_cancel_ref"] = weakref.ref(self, do_cancel)

    def as_iter(self):
        """Returns an iterator which individually yields each object in this
        page, and all subsequent pages.

        The iterator will block as needed if the current Pulp search has not
        yet completed.
        """
        page = self
        while True:
            for elem in page.data:
                yield elem
            if not page.next:
                return
            # blocks here if next page is not yet fetched
            page = page.next.result()
