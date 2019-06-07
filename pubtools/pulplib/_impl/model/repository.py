from .common import PulpObject, DetachedException


class PublishOptions(object):
    """Options controlling a repository
    :meth:`~pubtools.pulplib.Repository.publish`.
    """

    def __init__(self, force=False, clean=False):
        self.force = force
        """If True, Pulp should publish all data within a repository, rather than attempting
        to publish only changed data (or even skipping the publish).

        Setting ``force=True`` may have a major performance impact when publishing large repos.
        """

        self.clean = clean
        """If True, certain publish tasks will not only publish new/changed content, but
        will also attempt to erase formerly published content which is no longer present
        in the repo.

        Setting ``clean=True`` generally implies ``force=True``.
        """


class Repository(PulpObject):
    """Represents a Pulp repository."""

    @property
    def id(self):
        """ID of this repository (str)."""

    @property
    def created(self):
        """:class:`~datetime.datetime` in UTC at which this repository was created,
        or None if this information is unavailable.
        """

    def delete(self):
        """Delete this repository from Pulp.

        Returns:
            Future
                A future which is resolved when the repository deletion has completed.

                This object also becomes detached from the client; no further updates
                are possible.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.
        """

    def publish(self, options=None):
        """Publish this repository.

        The specific operations triggered on Pulp in order to publish a repo are not defined,
        but in Pulp 2.x, generally consists of triggering one or more distributors in sequence.

        Args:
            options (PublishOptions)
                Options used to customize the behavior of this publish.

                If omitted, reasonable defaults apply.

        Returns:
            Future[list[:class:`~pubtools.pulplib.Task`]]
                A future which is resolved when publish succeeds.

                The future contains a list of zero or more tasks triggered and awaited
                during the publish operation.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.
        """


# Design notes
# ============
#
# Semantics of publish is intentionally vague to increase the chance that the API
# might be reusable on Pulp 3, and might be able to cover various behavior changes
# requested in the future.
