import datetime
import logging

from more_executors.futures import f_map

from ..common import PulpObject, DetachedException
from ..attr import pulp_attrib
from ..distributor import Distributor
from ...schema import load_schema
from ... import compat_attr as attr


LOG = logging.getLogger("pubtools.pulplib")

REPO_CLASSES = {}


def repo_type(pulp_type):
    # decorator for Repository subclasses, registers against a
    # particular value of notes._repo-type
    def decorate(klass):
        REPO_CLASSES[pulp_type] = klass
        return klass

    return decorate


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

    origin_only = attr.ib(default=None, type=bool)
    """If ``True``, Pulp should only update the content units / origin path on
    remote hosts.

    Only relevant if a repository has one or more distributors where
    :meth:`~pubtools.pulplib.Distributor.is_rsync` is ``True``.
    """


@attr.s(kw_only=True, frozen=True)
class Repository(PulpObject):
    """Represents a Pulp repository."""

    _SCHEMA = load_schema("repository")

    # The distributors (by ID) which should be activated when publishing this repo.
    # Order matters. Distributors which don't exist will be ignored.
    _PUBLISH_DISTRIBUTORS = [
        "iso_distributor",
        "yum_distributor",
        "cdn_distributor",
        "cdn_distributor_unprotected",
        "docker_web_distributor_name_cli",
    ]

    id = pulp_attrib(type=str, pulp_field="id")
    """ID of this repository (str)."""

    type = pulp_attrib(default=None, type=str, pulp_field="notes._repo-type")
    """Type of this repository (str).

    This is a brief string denoting the content / Pulp plugin type used with
    this repository, e.g. ``rpm-repo``.
    """

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

    eng_product_id = pulp_attrib(
        default=None, type=int, pulp_field="notes.eng_product", pulp_py_converter=int
    )
    """ID of the product to which this repository belongs (if any)."""

    relative_url = attr.ib(default=None, type=str)
    """Default publish URL for this repository, relative to the Pulp content root."""

    mutable_urls = attr.ib(default=attr.Factory(list), type=list)
    """A list of URLs relative to repository publish root which are expected
    to change at every publish (if any content of repo changed)."""

    is_sigstore = attr.ib(default=False, type=bool)
    """True if this is a sigstore repository, used for container image manifest
    signatures."""

    signing_keys = pulp_attrib(
        default=attr.Factory(list),
        type=list,
        pulp_field="notes.signatures",
        pulp_py_converter=lambda sigs: sigs.split(","),
        converter=lambda keys: [k.strip() for k in keys],
    )
    """A list of GPG signing key IDs used to sign content in this repository."""

    skip_rsync_repodata = attr.ib(default=False, type=bool)
    """True if this repository is explicitly configured such that a publish of
    this repository will not publish repository metadata to remote hosts.
    """

    _client = attr.ib(default=None, init=False, repr=False, cmp=False)
    # hidden attribute for client attached to this object

    @property
    def _distributors_by_id(self):
        out = {}
        for dist in self.distributors:
            out[dist.id] = dist
        return out

    def distributor(self, distributor_id):
        """Look up a distributor by ID.

        Returns:
            :class:`~pubtools.pulplib.Distributor`
                The distributor belonging to this repository with the given ID.
            None
                If this repository has no distributor with the given ID.
        """
        return self._distributors_by_id.get(distributor_id)

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
        candidate_distributor_ids = self._PUBLISH_DISTRIBUTORS

        to_publish = []

        for candidate in candidate_distributor_ids:
            distributor = self._distributors_by_id.get(candidate)
            if not distributor:
                # nothing to be done
                continue

            if (
                distributor.id == "docker_web_distributor_name_cli"
                and options.origin_only
            ):
                continue

            config = self._config_for_distributor(distributor, options)
            to_publish.append((distributor, config))

        return self._client._publish_repository(self, to_publish)

    @classmethod
    def from_data(cls, data):
        # delegate to concrete subclass as needed
        if cls is Repository:
            notes = data.get("notes") or {}
            for notes_type, klass in REPO_CLASSES.items():
                if notes.get("_repo-type") == notes_type:
                    return klass.from_data(data)

        return super(Repository, cls).from_data(data)

    @classmethod
    def _data_to_init_args(cls, data):
        out = super(Repository, cls)._data_to_init_args(data)

        for dist in data.get("distributors") or []:
            if dist["distributor_type_id"] in ("yum_distributor", "iso_distributor"):
                out["relative_url"] = (dist.get("config") or {}).get("relative_url")

            if dist["id"] == "cdn_distributor":
                skip_repodata = (dist.get("config") or {}).get("skip_repodata")
                if skip_repodata is not None:
                    out["skip_rsync_repodata"] = skip_repodata

        return out

    @classmethod
    def _config_for_distributor(cls, distributor, options):
        out = {}

        if options.clean is not None and distributor.is_rsync:
            out["delete"] = options.clean

        if options.origin_only is not None and distributor.is_rsync:
            out["content_units_only"] = options.origin_only

        if options.force is not None:
            out["force_full"] = options.force

        return out
