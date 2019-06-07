class FakeController(object):
    """A controller for a fake :class:`~pubtools.pulplib.Client`, to be used
    within automated tests.

    This class provides a client which has the same public interface as
    :class:`~pubtools.pulplib.Client`. This client is fully functional for
    both reads and writes, but uses a simple in-memory implementation rather
    than issuing requests to a remote Pulp server. The client's data may be
    inspected and modified via the FakeController instance.

    Example:

        .. code-block:: python

            # imagine we have a function like this
            def delete_old_repos(client, days):
                # code here using client to find/delete all repos older
                # than given number of days
                ...

            # then we can use a fake client to test it like this
            def test_delete_old_repos():
                controller = FakeController()

                # Insert repositories into fake data
                repo_now = Repository(id='current-repo', created=datetime.utcnow())
                repo_old = Repository(id='old-repo', created=datetime.min)

                controller.insert_repository(repo_now)
                controller.insert_repository(repo_old)

                # Run the code under test against the fake client

                # It should succeed without crashing
                delete_old_repos(controller.client, 5)

                # The set of repos should now contain only the recent repo
                assert controller.repositories == [repo_now]

    """

    def insert_repository(self, repository):
        """Add a repository to the set of existing repositories in the fake client.

        Args:
            repository (:class:`~pubtools.pulplib.Repository`)
                A repository object to insert.
        """

    @property
    def repositories(self):
        """The list of existing repositories in the fake client."""

    @property
    def client(self):
        """The client instance attached to this controller."""

    # TODO: some kind of publish reports should be exposed here too,
    # since the client has publish functionality.
    # Or should we rather implement methods in the client to fetch
    # a publish report, since Pulp does have API for that?


# Design notes
# ============
#
# The existence of this class is a reaction to the overuse of mocking in existing
# Pulp client code. Mocks are very powerful but lead to major maintenance problems:
# it's common to mock a specific method call sequence, unnecessarily tying a test
# to certain implementation details. This results in tests which wrongly fail when
# the sequence of method calls is changed to an equally valid alternative sequence.
# Even worse, it can result in tests which wrongly pass since the default behavior
# of MagicMock is for all method calls to succeed even if provided garbage input.
#
# The fake client is meant to address this by ensuring that, for any code written
# against the pulplib client, it's possible to swap in a client which is "fake" in
# that it doesn't query to a real Pulp server, but "real" in that the usual CRUD
# operations do work as normal, arguments have to be the correct type or exceptions
# will be raised, and so on.
#
# The FakeController could potentially be extended to allow certain behaviors of the
# client to be customized (e.g. introduce fake delays to Pulp operations).
#
# If the caller wants to test error conditions, the likely approach will be to mix
# mocks with the fake client. For example, make a fake controller & client but then
# mock.patch individual methods to return errors when needed.
#
