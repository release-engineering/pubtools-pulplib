import datetime
import logging

from more_executors.futures import f_map

from .common import PulpObject, DetachedException
from .attr import pulp_attrib
from .distributor import Distributor
from ..schema import load_schema
from .. import compat_attr as attr


LOG = logging.getLogger("pubtools.pulplib")


@attr.s(kw_only=True, frozen=True)
class PublishOptions(object):
    """Options controlling a repository
    :meth:`~pubtools.pulplib.Repository.publish`.
    """

    force = attr.ib(default=None, type=bool)
    """If True, Pulp should publish all data within a repository, rather than attempting
    to publish only changed data (or even skipping the publish).

    Setting ``force=True`` may have a major performance impact when publishing large repos.
    """

    clean = attr.ib(default=None, type=bool)
    """If True, certain publish tasks will not only publish new/changed content, but
    will also attempt to erase formerly published content which is no longer present
    in the repo.

    Setting ``clean=True`` generally implies ``force=True``.
    """


@attr.s(kw_only=True, frozen=True)
class Repository(PulpObject):
    """Represents a Pulp repository."""

    _SCHEMA = load_schema("repository")

    id = pulp_attrib(type=str, pulp_field="id")
    """ID of this repository (str)."""

    created = pulp_attrib(
        default=None, type=datetime.datetime, pulp_field="notes.created"
    )
    """:class:`~datetime.datetime` in UTC at which this repository was created,
    or None if this information is unavailable.
    """

    distributors = pulp_attrib(
        default=attr.Factory(tuple),
        type=tuple,
        pulp_field="distributors",
        pulp_py_converter=lambda ds: tuple([Distributor.from_data(d) for d in ds]),
        # It's too noisy to let repr descend into sub-objects
        repr=False,
    )
    """tuple of :class:`~pubtools.pulplib.Distributor` objects belonging to this
    repository.
    """

    _client = attr.ib(default=None, init=False, repr=False, cmp=False)
    # hidden attribute for client attached to this object

    @property
    def distributors_by_id(self):
        out = {}
        for dist in self.distributors:
            out[dist.id] = dist
        return out

    def delete(self):
        """Delete this repository from Pulp.

        Returns:
            Future[list[:class:`~pubtools.pulplib.Task`]]
                A future which is resolved when the repository deletion has completed.

                The future contains a list of zero or more tasks triggered and awaited
                during the delete operation.

                This object also becomes detached from the client; no further updates
                are possible.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.
        """
        if not self._client:
            raise DetachedException()

        delete_f = self._client._delete_resource("repositories", self.id)

        def detach(tasks):
            LOG.debug("Detaching %s after successful delete", self)
            self.__dict__["_client"] = None
            return tasks

        return f_map(delete_f, detach)

    def publish(self, options=PublishOptions()):
        """Publish this repository.

        The specific operations triggered on Pulp in order to publish a repo are not defined,
        but in Pulp 2.x, generally consists of triggering one or more distributors in sequence.

        Args:
            options (PublishOptions)
                Options used to customize the behavior of this publish.

                If omitted, the Pulp server's defaults apply.

        Returns:
            Future[list[:class:`~pubtools.pulplib.Task`]]
                A future which is resolved when publish succeeds.

                The future contains a list of zero or more tasks triggered and awaited
                during the publish operation.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.
        """
        if not self._client:
            raise DetachedException()

        # all distributor IDs we're willing to invoke. Anything else is ignored.
        # They'll be invoked in the order listed here.
        candidate_distributor_ids = [
            "yum_distributor",
            "iso_distributor",
            "cdn_distributor",
            "docker_web_distributor_name_cli",
        ]

        to_publish = []

        for candidate in candidate_distributor_ids:
            distributor = self.distributors_by_id.get(candidate)
            if not distributor:
                # nothing to be done
                continue

            config = self._config_for_distributor(distributor, options)
            to_publish.append((distributor, config))

        return self._client._publish_repository(self, to_publish)

    @classmethod
    def _config_for_distributor(cls, distributor, options):
        out = {}

        if options.clean is not None and distributor.is_rsync:
            out["delete"] = options.clean

        if options.force is not None:
            out["force_full"] = options.force

        return out


# Design notes
# ============
#
# Semantics of publish is intentionally vague to increase the chance that the API
# might be reusable on Pulp 3, and might be able to cover various behavior changes
# requested in the future.
