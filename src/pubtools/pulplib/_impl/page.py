import logging
import weakref
import warnings
from concurrent.futures import Future

from frozenlist2 import frozenlist


from . import compat_attr as attr
from .model.attr import pulp_attrib

LOG = logging.getLogger("pubtools.pulplib")


# pylint shows these spurious errors on this file, not sure why:
# page.py:86:23: E1101: Instance of '_CountingAttr' has no 'done' member (no-member)
# Could be due to bug https://github.com/PyCQA/pylint/issues/1694 ?
# pylint: disable=no-member


@attr.s(kw_only=True, frozen=True, slots=False)
class Page(object):
    """A page of Pulp search results.

    All Pulp searches issued by this library are paginated.
    Instances of this class may be used to iterate through the returned
    pages, in both blocking and non-blocking coding styles.

    Page objects are iterables. Iterating over a page will iterate
    over all data within that page, *and all subsequent pages*,
    blocking on more data from Pulp as needed.

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

        This example uses the page as an iterable to loop over all search
        results. At certain points during the iteration, blocking may
        occur to await more pages from Pulp.

        .. code-block:: python

            page = client.search_repository(...).result()
            # processes all data, but may block at page boundaries
            for repo in page:
                do_something(repo)

    """

    data = pulp_attrib(
        default=attr.Factory(frozenlist), type=list, converter=frozenlist
    )
    """List of Pulp objects in this page.

    This list will contain instances of the appropriate Pulp object type
    (e.g. :class:`~pubtools.pulplib.Repository` for a repository search).
    """

    next = pulp_attrib(default=None, type=Future)
    """None, if this is the last page of results.

    Otherwise, a Future[:class:`Page`] for the next page of results.
    """

    def __attrs_post_init__(self):
        if self.next:
            # We have a next, which means there are subsequent pages currently being
            # searched for.
            #
            # If *this* page disappears, and 'next' hasn't been accessed by that time,
            # it's pointless to keep querying for the next page, so we could
            # cancel that future.
            #
            # Note: when we are Py3-only, this could be better rewritten
            # using weakref.finalize or even just plain __del__

            to_cancel = self.next

            # We're going to use self.__dict__, but we must avoid capturing
            # a reference to self in do_cancel since that would be a cycle.
            stash = self.__dict__

            def do_cancel(*_):
                if stash.get("_should_cancel") and not to_cancel.done():
                    cancel_result = to_cancel.cancel()
                    LOG.debug("Cancel next page due to GC: %s", cancel_result)

            # Just stash a weakref anywhere it'll stay alive for as long
            # as the page itself.
            stash["_should_cancel"] = True
            stash["_cancel_ref"] = weakref.ref(self, do_cancel)

    def as_iter(self):
        # TODO: remove me. Originally deprecated 2019-09.
        warnings.warn(
            "as_iter is deprecated, use page as iterable instead", DeprecationWarning
        )

        return self.__iter__()

    def __iter__(self):
        page = self
        while True:
            for elem in page.data:
                yield elem
            if not page.next:
                return
            # blocks here if next page is not yet fetched
            page = page.next.result()


# Wrap any access to 'next' to avoid cancellation.
#
# When initially created, we are in a state where we potentially have a search
# in progress for the next page, but we might cancel it if we're GC'd.
# As soon as someone references 'next' though, we can no longer safely do such
# a cancellation.
#
# This has to be installed as a property dynamically after class creation, since
# attrs will not generate the 'next' attribute normally if it sees that a next
# @property was already defined.
def page_next(self):
    self.__dict__.pop("_should_cancel", None)
    return self.__dict__["next"]


def page_set_next(self, value):  # pragma: no cover
    # A setter seems to be needed for compatibility with attrs on py2
    # because we can't use 'frozen' there, but this is never reached
    # on py3. Hence the no cover pragma.
    self.__dict__["next"] = value


Page.next = property(page_next, page_set_next)
