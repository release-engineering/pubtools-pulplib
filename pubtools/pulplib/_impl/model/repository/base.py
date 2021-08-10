import datetime
import logging

from attr import validators, asdict
from more_executors.futures import f_proxy, f_map

from ..common import PulpObject, Deletable, DetachedException
from ..attr import pulp_attrib
from ..distributor import Distributor
from ..frozenlist import FrozenList
from ...criteria import Criteria, Matcher
from ...schema import load_schema
from ... import compat_attr as attr
from ...hooks import pm


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

    force = pulp_attrib(default=None, type=bool)
    """If True, Pulp should publish all data within a repository, rather than attempting
    to publish only changed data (or even skipping the publish).

    Setting ``force=True`` may have a major performance impact when publishing large repos.
    """

    clean = pulp_attrib(default=None, type=bool)
    """If True, certain publish tasks will not only publish new/changed content, but
    will also attempt to erase formerly published content which is no longer present
    in the repo.

    Setting ``clean=True`` generally implies ``force=True``.
    """

    origin_only = pulp_attrib(default=None, type=bool)
    """If ``True``, Pulp should only update the content units / origin path on
    remote hosts.

    Only relevant if a repository has one or more distributors where
    :meth:`~pubtools.pulplib.Distributor.is_rsync` is ``True``.
    """


@attr.s(kw_only=True, frozen=True)
class SyncOptions(object):
    """Options controlling a repository
    :meth:`~pubtools.pulplib.Repository.sync`.

    .. seealso:: Subclasses for specific repository
                 types: :py:class:`~pubtools.pulplib.FileSyncOptions`,
                 :py:class:`~pubtools.pulplib.YumSyncOptions`,
                 :py:class:`~pubtools.pulplib.ContainerSyncOptions`
    """

    feed = pulp_attrib(type=str)
    """URL where the repository's content will be synchronized from.
    """

    ssl_validation = pulp_attrib(default=None, type=bool)
    """Indicates if the server's SSL certificate is verified against the CA certificate uploaded.
    """

    ssl_ca_cert = pulp_attrib(default=None, type=str)
    """CA certificate string used to validate the feed source's SSL certificate
    """

    ssl_client_cert = pulp_attrib(default=None, type=str)
    """Certificate used as the client certificate when synchronizing the repository
    """

    ssl_client_key = pulp_attrib(default=None, type=str)
    """Private key to the certificate specified in ssl_client_cert
    """

    max_speed = pulp_attrib(default=None, type=int)
    """The maximum download speed in bytes/sec for a task (such as a sync).

    Default is None
    """

    proxy_host = pulp_attrib(default=None, type=str)
    """A string representing the URL of the proxy server that should be used when synchronizing
    """

    proxy_port = pulp_attrib(default=None, type=int)
    """An integer representing the port that should be used when connecting to proxy_host.
    """

    proxy_username = pulp_attrib(default=None, type=str)
    """A string representing the username that should be used to authenticate with the proxy server
    """

    proxy_password = pulp_attrib(default=None, type=str)
    """A string representing the password that should be used to authenticate with the proxy server
    """


@attr.s(kw_only=True, frozen=True)
class Repository(PulpObject, Deletable):
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
        default=attr.Factory(FrozenList),
        type=list,
        pulp_field="distributors",
        converter=FrozenList,
        pulp_py_converter=lambda ds: FrozenList([Distributor.from_data(d) for d in ds]),
        # It's too noisy to let repr descend into sub-objects
        repr=False,
    )
    """list of :class:`~pubtools.pulplib.Distributor` objects belonging to this
    repository.
    """

    eng_product_id = pulp_attrib(
        default=None,
        type=int,
        pulp_field="notes.eng_product",
        pulp_py_converter=int,
        py_pulp_converter=str,
    )
    """ID of the product to which this repository belongs (if any)."""

    relative_url = pulp_attrib(default=None, type=str)
    """Default publish URL for this repository, relative to the Pulp content root."""

    mutable_urls = pulp_attrib(
        default=attr.Factory(FrozenList), type=list, converter=FrozenList
    )
    """A list of URLs relative to repository publish root which are expected
    to change at every publish (if any content of repo changed)."""

    is_sigstore = pulp_attrib(default=False, type=bool)
    """True if this is a sigstore repository, used for container image manifest
    signatures."""

    is_temporary = pulp_attrib(
        default=False,
        type=bool,
        validator=validators.instance_of(bool),
        pulp_field="notes.pub_temp_repo",
    )
    """True if this is a temporary repository.

    A temporary repository is a repository created by release-engineering tools
    for temporary use during certain workflows.  Such repos are not expected to
    be published externally and generally should have a lifetime of a few days
    or less.

    .. versionadded:: 1.3.0
    """

    signing_keys = pulp_attrib(
        default=attr.Factory(FrozenList),
        type=list,
        pulp_field="notes.signatures",
        pulp_py_converter=lambda sigs: sigs.split(","),
        py_pulp_converter=",".join,
        converter=lambda keys: FrozenList([k.strip() for k in keys]),
    )
    """A list of GPG signing key IDs used to sign content in this repository."""

    skip_rsync_repodata = pulp_attrib(default=False, type=bool)
    """True if this repository is explicitly configured such that a publish of
    this repository will not publish repository metadata to remote hosts.
    """

    content_set = pulp_attrib(default=None, type=str, pulp_field="notes.content_set")
    """Name of content set that is associated with this repository."""

    @distributors.validator
    def _check_repo_id(self, _, value):
        # checks if distributor's repository id is same as the repository it
        # is attached to
        for distributor in value:
            if not distributor.repo_id:
                return
            if distributor.repo_id == self.id:
                return
            raise ValueError(
                "repo_id doesn't match for %s. repo_id: %s, distributor.repo_id: %s"
                % (distributor.id, self.id, distributor.repo_id)
            )

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

    @property
    def file_content(self):
        """A list of file units stored in this repository.

        Returns:
            list[:class:`~pubtools.pulplib.FileUnit`]

        .. versionadded:: 2.4.0
        """
        return list(self.search_content(Criteria.with_field("content_type_id", "iso")))

    @property
    def rpm_content(self):
        """A list of rpm units stored in this repository.

        Returns:
            list[:class:`~pubtools.pulplib.RpmUnit`]

        .. versionadded:: 2.4.0
        """
        return list(self.search_content(Criteria.with_field("content_type_id", "rpm")))

    @property
    def srpm_content(self):
        """A list of srpm units stored in this repository.

        Returns:
            list[:class:`~pubtools.pulplib.Unit`]

        .. versionadded:: 2.4.0
        """
        return list(self.search_content(Criteria.with_field("content_type_id", "srpm")))

    @property
    def modulemd_content(self):
        """A list of modulemd units stored in this repository.

        Returns:
            list[:class:`~pubtools.pulplib.ModulemdUnit`]

        .. versionadded:: 2.4.0
        """
        return list(
            self.search_content(Criteria.with_field("content_type_id", "modulemd"))
        )

    @property
    def modulemd_defaults_content(self):
        """A list of modulemd_defaults units stored in this repository.

        Returns:
            list[:class:`~pubtools.pulplib.ModulemdDefaultsUnit`]

        .. versionadded:: 2.4.0
        """
        return list(
            self.search_content(
                Criteria.with_field("content_type_id", "modulemd_defaults")
            )
        )

    def search_content(self, criteria=None):
        """Search this repository for content matching the given criteria.

        Args:
            criteria (:class:`~pubtools.pulplib.Criteria`)
                A criteria object used for this search.

        Returns:
            Future[:class:`~pubtools.pulplib.Page`]
                A future representing the first page of results.

                Each page will contain a collection of
                :class:`~pubtools.pulplib.Unit` objects.

        .. versionadded:: 2.4.0
        """
        if not self._client:
            raise DetachedException()

        return self._client._search_repo_units(self.id, criteria)

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
        return self._delete("repositories", self.id)

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

        out = self._client._publish_repository(self, to_publish)

        def do_published_hook(tasks):
            # Whenever we've published successfully, we'll activate this hook
            # before returning.
            pm.hook.pulp_repository_published(repository=self, options=options)
            return tasks

        out = f_map(out, do_published_hook)
        return f_proxy(out)

    def sync(self, options=None):
        """Sync repository with feed.

        Args:
            options (SyncOptions)
                Options used to customize the behavior of sync process.
                If omitted, the Pulp server's defaults apply.

        Returns:
            Future[list[:class:`~pubtools.pulplib.Task`]]
                A future which is resolved when sync succeeds.

                The future contains a list of zero or more tasks triggered and awaited
                during the sync operation.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.

        .. versionadded:: 2.5.0
        """
        options = options or SyncOptions(feed="")

        if not self._client:
            raise DetachedException()

        return f_proxy(
            self._client._do_sync(
                self.id, asdict(options, filter=lambda name, val: val is not None)
            )
        )

    def remove_content(self, **kwargs):
        """Remove all content of requested types from this repository.

        Args:
            type_ids (list[str])
                IDs of content type(s) to be removed.
                See :meth:`~pubtools.pulplib.Client.get_content_type_ids`.

                If omitted, content of all types will be removed.

        Returns:
            Future[list[:class:`~pubtools.pulplib.Task`]]
                A future which is resolved when content has been removed.

                The future contains a list of zero or more tasks triggered and awaited
                during the removal.

                To obtain information on the removed content, use
                :meth:`~pubtools.pulplib.Task.units`.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.

        .. versionadded:: 1.5.0
        """
        if not self._client:
            raise DetachedException()

        # Note: we use dynamic kwargs because it's very likely that a future
        # version of this method will support some "criteria".  Let's not fix the
        # argument order at least until then.

        # start down the path of using Criteria per this issue:
        # https://github.com/release-engineering/pubtools-pulplib/issues/62
        # by using Criteria internally.
        # there seems to be pretty complex handling of Criteria
        # for serialization in the search API, and it is unclear which parts
        # might also be necessary to use for content removal.
        # If any or all of the same handling is needed, it would be beneficial
        # to encapsulate the preparation of a criteria JSON object in some
        # (more generically named) functions or a class to avoid duplicating code.
        # for reference see search_content, _impl.client.Client._search_repo_units,
        # _impl.client.Client._search, and _impl.client.search.search_for_criteria
        criteria = None
        type_ids = kwargs.get("type_ids")
        # use _content_type_id field name to coerce
        # search_for_criteria to fill out the PulpSearch#type_ids field.
        # passing a criteria with an empty type_ids list rather than
        # None results in failing tests due to the implementation of
        # FakeClient#_do_unassociate
        if type_ids is not None:
            criteria = Criteria.with_field(
                "_content_type_id",
                Matcher.in_(type_ids),  # Criteria.with_field_in is deprecated
            )

        return f_proxy(self._client._do_unassociate(self.id, criteria=criteria))

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

    def _set_client(self, client):
        super(Repository, self)._set_client(client)

        # distributors use the same client as owning repository
        for distributor in self.distributors or []:
            distributor._set_client(client)
