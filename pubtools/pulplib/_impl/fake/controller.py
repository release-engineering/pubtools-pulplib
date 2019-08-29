from .client import FakeClient


class FakeController(object):
    """A controller for a fake :class:`~pubtools.pulplib.Client`, to be used
    within automated tests.

    This class provides a client which has the same public interface as
    :class:`~pubtools.pulplib.Client`. This client can do most of the same
    actions as a real client, but uses a simple in-memory implementation rather
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
                repo_now = YumRepository(id='current-repo', created=datetime.utcnow())
                repo_old = FileRepository(id='old-repo', created=datetime.min)

                controller.insert_repository(repo_now)
                controller.insert_repository(repo_old)

                # Run the code under test against the fake client

                # It should succeed without crashing
                delete_old_repos(controller.client, 5)

                # The set of repos should now contain only the recent repo
                assert controller.repositories == [repo_now]

    **Limitations:**

        While :class:`~pubtools.pulplib.Client` allows searching on any fields
        which exist within Pulp's database, the fake client only supports searching
        on fields known to the :ref:`schemas` used by this library.
    """

    def __init__(self):
        self.client = FakeClient()
        """The client instance attached to this controller."""

    @property
    def repositories(self):
        """The list of existing repositories in the fake client."""
        return self.client._repositories[:]

    def insert_repository(self, repository):
        """Add a repository to the set of existing repositories in the fake client.

        Args:
            repository (:class:`~pubtools.pulplib.Repository`)
                A repository object to insert.
        """
        self.client._repositories.append(repository)

    @property
    def content_type_ids(self):
        """The list of content type IDs the fake client will claim to support.

        .. versionadded:: 1.4.0
        """
        return self.client._type_ids[:]

    def set_content_type_ids(self, type_ids):
        """Set the list of content type IDs the fake client will claim to support.

        Args:
            type_ids (list[str])
                A list of content type IDs (e.g. "rpm", "erratum", ...)

        .. versionadded:: 1.4.0
        """
        self.client._type_ids = type_ids[:]

    @property
    def publish_history(self):
        """A list of repository publishes triggered via this client.

        Each element of this list is a named tuple with the following attributes,
        in order:

            ``repository``:
                :class:`~pubtools.pulplib.Repository` for which publish was triggered
            ``tasks``:
                list of :class:`~pubtools.pulplib.Task` generated as a result
                of this publish
        """
        return self.client._publish_history[:]

    @property
    def upload_history(self):
        """A list of upload tasks triggered via this client.

        Each element of this list is a named tuple with the following attributes,
        in order:

            ``repository``:
                :class:`~pubtools.pulplib.Repository` for which upload was triggered
            ``tasks``:
                list of :class:`~pubtools.pulplib.Task` generated as a result
                of this upload
            ``name`` (str):
                the remote path used
            ``sha256`` (str):
                checksum of the file uploaded
        """
        return self.client._upload_history[:]
