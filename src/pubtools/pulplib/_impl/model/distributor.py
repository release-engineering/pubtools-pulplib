import datetime

from .common import PulpObject, Deletable, DetachedException
from .attr import pulp_attrib
from ..schema import load_schema
from .. import compat_attr as attr


@attr.s(kw_only=True, frozen=True)
class Distributor(PulpObject, Deletable):
    """Represents a Pulp distributor."""

    _SCHEMA = load_schema("repository", "distributor")

    id = pulp_attrib(type=str, pulp_field="id")
    """ID of this distributor (str).

    This is an arbitrary string, though often matches exactly the `type_id`.
    """

    type_id = pulp_attrib(type=str, pulp_field="distributor_type_id")
    """Type ID of this distributor (str).

    The type ID of a distributor determines which content may be handled and
    which steps may be performed by the distributor. For example, distributors
    of type `yum_distributor` may be used to create yum repositories.
    """

    repo_id = pulp_attrib(type=str, default=None, pulp_field="repo_id")
    """The :class:`pubtools.pulplib.Repository` ID this distributor is attached to."""

    relative_url = pulp_attrib(type=str, default=None, pulp_field="config.relative_url")
    """Default distribution URL for the repository which the distributor is attached to,
    relative to the Pulp content root."""

    last_publish = pulp_attrib(
        default=None, type=datetime.datetime, pulp_field="last_publish"
    )
    """The :class:`~datetime.datetime` at which this distributor was last published,
    if known."""

    is_rsync = attr.ib(
        default=attr.Factory(
            lambda self: self.type_id
            in (
                "rpm_rsync_distributor",
                "iso_rsync_distributor",
                "docker_rsync_distributor",
            ),
            takes_self=True,
        )
    )
    """True for distributors in the 'rsync distributor' family
    (e.g. ``rpm_rsync_distributor``).
    """

    def delete(self):
        """Delete this distributor from Pulp.

        Returns:
            Future[list[:class:`~pubtools.pulplib.Task`]]
                A future which is resolved when the distributor deletion has completed.

                The future contains a list of zero or more tasks triggered and awaited
                during the delete operation.

                This object also becomes detached from the client; no further updates
                are possible.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client or repository.

        .. versionadded:: 2.3.0
        """
        if not self.repo_id:
            raise DetachedException()

        return self._delete("repositories/%s/distributors" % self.repo_id, self.id)
