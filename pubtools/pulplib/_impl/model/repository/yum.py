import re

import six
from frozenlist2 import frozenlist

from more_executors.futures import f_map, f_proxy, f_return
from .base import Repository, SyncOptions, repo_type
from ..attr import pulp_attrib
from ..common import DetachedException
from ... import compat_attr as attr
from ...criteria import Criteria


@attr.s(kw_only=True, frozen=True)
class YumSyncOptions(SyncOptions):
    """Options controlling a yum repository
    :meth:`~pubtools.pulplib.Repository.sync`.
    """

    query_auth_token = pulp_attrib(default=None, type=str)
    """An authorization token that will be added to every request made to the feed URL's server
    """

    max_downloads = pulp_attrib(default=None, type=int)
    """Number of threads used when synchronizing the repository.
    """

    remove_missing = pulp_attrib(default=None, type=bool)
    """If true, as the repository is synchronized, old rpms will be removed.
    """

    retain_old_count = pulp_attrib(default=None, type=int)
    """Count indicating how many old rpm versions to retain.
    """

    skip = pulp_attrib(default=None, type=list)
    """List of content types to be skipped during the repository synchronization
    """

    checksum_type = pulp_attrib(default=None, type=str)
    """checksum type to use for metadata generation.

    Defaults to source checksum type of sha256
    """

    num_retries = pulp_attrib(default=None, type=int)
    """Number of times to retry before declaring an error during repository synchronization

    Default is 2.
    """

    download_policy = pulp_attrib(default=None, type=str)
    """Set the download policy for a repository.

    Supported options are immediate,on_demand,background
    """

    force_full = pulp_attrib(default=None, type=bool)
    """Boolean flag. If true, full re-sync is triggered.
    """

    require_signature = pulp_attrib(default=None, type=bool)
    """Requires that imported packages like RPM/DRPM/SRPM should be signed
    """

    allowed_keys = pulp_attrib(default=None, type=list)
    """List of allowed signature key IDs that imported packages can be signed with
    """


@repo_type("rpm-repo")
@attr.s(kw_only=True, frozen=True)
class YumRepository(Repository):
    """A :class:`~pubtools.pulplib.Repository` for RPMs, errata and related content."""

    # this class only overrides some defaults for attributes defined in super

    type = pulp_attrib(default="rpm-repo", type=str, pulp_field="notes._repo-type")

    population_sources = pulp_attrib(
        default=attr.Factory(frozenlist),
        type=list,
        converter=frozenlist,
        pulp_field="notes.population_sources",
    )
    """List of repository IDs used to populate this repository
    """

    ubi_population = pulp_attrib(
        default=False, type=bool, pulp_field="notes.ubi_population"
    )
    """Flag indicating whether repo should be populated from population_sources for the purposes of UBI
    """

    mutable_urls = attr.ib(
        default=attr.Factory(lambda: frozenlist(["repodata/repomd.xml"])),
        type=list,
        converter=frozenlist,
    )

    ubi_config_version = pulp_attrib(
        default=None, type=str, pulp_field="notes.ubi_config_version"
    )
    """Version of UBI config that should be used for population of this repository."""

    def get_binary_repository(self):
        """Find and return the binary repository relating to this repository.

        Yum repositories usually come in triplets of
        (binary RPMs, debuginfo RPMs, source RPMs). For example:

        .. list-table::
            :widths: 75 25

            * - ``rhel-7-server-rpms__7Server__x86_64``
              - binary
            * - ``rhel-7-server-debug-rpms__7Server__x86_64``
              - debug
            * - ``rhel-7-server-source-rpms__7Server__x86_64``
              - source

        This method along with :meth:`get_debug_repository` and :meth:`get_source_repository` allow locating other repositories
        from within this group.

        Returns:
            ``Future[YumRepository]``
                Binary repository relating to this repository.
            ``Future[None]``
                If there is no related repository.
        """
        return self._get_related_repository(repo_t="binary")

    def get_debug_repository(self):
        """Find and return the debug repository relating to this repository.

        Returns:
            ``Future[YumRepository]``
                Debug repository relating to this repository.
            ``Future[None]``
                If there is no related repository.
        """
        return self._get_related_repository(repo_t="debug")

    def get_source_repository(self):
        """Find and return the source repository relating to this repository.

        Returns:
            ``Future[YumRepository]``
                Source repository relating to this repository.
            ``Future[None]``
                If there is no related repository.
        """
        return self._get_related_repository(repo_t="source")

    def _get_related_repository(self, repo_t):
        if not self._client:
            raise DetachedException()

        suffixes_mapping = {
            "binary": "/os",
            "debug": "/debug",
            "source": "/source/SRPMS",
        }

        regex = r"(/os|/source/SRPMS|/debug)$"

        def unpack_page(page):
            if len(page.data) != 1:
                return None

            return page.data[0]

        suffix = suffixes_mapping[repo_t]
        if str(self.relative_url).endswith(suffix):
            return f_proxy(f_return(self))

        base_url = re.sub(regex, "", self.relative_url)
        relative_url = base_url + suffix
        criteria = Criteria.with_field("notes.relative_url", relative_url)
        page_f = self._client.search_repository(criteria)
        repo_f = f_map(page_f, unpack_page)
        return f_proxy(repo_f)

    def upload_rpm(self, file_obj):
        """Upload an RPM to this repository.

        .. warning::

            For RPMs belonging to a module, it's strongly advised to upload
            the module metadata first (using :meth:`upload_modules`) and only
            proceed with uploading RPMs once module upload has completed.

            This reduces the risk of accidentally publishing a repository with
            modular RPMs without the corresponding metadata (which has a much
            worse impact than publishing metadata without the corresponding RPMs).

        Args:
            file_obj (str, file object)
                If it's a string, then it's the path of an RPM to upload.

                Otherwise, it should be a
                `file-like object <https://docs.python.org/3/glossary.html#term-file-object>`_
                pointing at the bytes to upload.
                The client takes ownership of this file object; it should
                not be modified elsewhere, and will be closed when upload
                completes.

        Returns:
            Future[list of :class:`~pubtools.pulplib.Task`]
                A future which is resolved after content has been imported
                to this repo.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.

        .. versionadded:: 2.16.0
        """
        # We want some name of what we're uploading for logging purposes, but the
        # input could be a plain string, or a file object with 'name' attribute, or
        # a file object without 'name' ... make sure we do something reasonable in
        # all cases.
        if isinstance(file_obj, six.string_types):
            name = file_obj
        else:
            # If we don't know what we're uploading we just say it's "an RPM"...
            name = getattr(file_obj, "name", "an RPM")

        return self._upload_then_import(file_obj, name, "rpm")

    def upload_metadata(self, file_obj, metadata_type):
        """Upload a metadata file to this repository.

        A metadata file is any additional file which will be published alongside,
        and referenced from, the repodata ``.xml`` and ``.sqlite`` files when this
        repo is published.

        Args:
            file_obj (str, file object)
                If it's a string, then it's the path of a file to upload.

                Otherwise, it should be a
                `file-like object <https://docs.python.org/3/glossary.html#term-file-object>`_
                pointing at the bytes to upload.
                The client takes ownership of this file object; it should
                not be modified elsewhere, and will be closed when upload
                completes.

            metadata_type (str)
                Identifies the type of metadata being uploaded.

                This is an arbitrary string which will be reproduced in the yum
                repo metadata on publish. The appropriate value depends on the
                type of data being uploaded. For example, ``"productid"`` should
                be used when uploading an RHSM-style product certificate.

                A repository may only contain a single metadata file of each type.
                If a file of this type is already present in the repo, it will be
                overwritten by the upload.

        Returns:
            Future[list of :class:`~pubtools.pulplib.Task`]
                A future which is resolved after content has been imported
                to this repo.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.

        .. versionadded:: 2.17.0
        """
        if isinstance(file_obj, six.string_types):
            name = "%s (%s)" % (file_obj, metadata_type)
        else:
            # If we don't know what we're uploading we just say "<type> metadata"...
            name = getattr(file_obj, "name", "%s metadata" % metadata_type)

        return self._upload_then_import(
            file_obj,
            name,
            "yum_repo_metadata_file",
            # Requirements around unit key and metadata can be found at:
            # https://github.com/pulp/pulp_rpm/blob/5c5a7dcc058b29d89b3a913d29cfcab41db96686/plugins/pulp_rpm/plugins/importers/yum/upload.py#L246
            unit_key_fn=lambda _: {"data_type": metadata_type, "repo_id": self.id},
            unit_metadata_fn=lambda upload: {
                "checksum": upload[0],
                "checksum_type": "sha256",
            },
        )

    def upload_modules(self, file_obj):
        """Upload a modulemd stream to this repository.

        All supported documents in the given stream will be imported to this
        repository. On current versions of Pulp 2.x, this means only:

        * `modulemd v2 <https://github.com/fedora-modularity/libmodulemd/blob/main/yaml_specs/modulemd_stream_v2.yaml>`_
        * `modulemd-defaults v1 <https://github.com/fedora-modularity/libmodulemd/blob/main/yaml_specs/modulemd_defaults_v1.yaml>`_

        Attempting to use other document types may result in an error.

        Args:
            file_obj (str, file object)
                If it's a string, then it's the path of a modulemd YAML
                file to upload.

                Otherwise, it should be a
                `file-like object <https://docs.python.org/3/glossary.html#term-file-object>`_
                pointing at the text to upload.
                The client takes ownership of this file object; it should
                not be modified elsewhere, and will be closed when upload
                completes.

        Returns:
            Future[list of :class:`~pubtools.pulplib.Task`]
                A future which is resolved after content has been imported
                to this repo.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.

        .. versionadded:: 2.17.0
        """
        if isinstance(file_obj, six.string_types):
            name = file_obj
        else:
            name = getattr(file_obj, "name", "modulemds")

        return self._upload_then_import(file_obj, name, "modulemd")
