import re

from more_executors.futures import f_map, f_proxy, f_return
from .base import Repository, SyncOptions, repo_type
from ..frozenlist import FrozenList
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
        default=attr.Factory(FrozenList),
        type=list,
        converter=FrozenList,
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
        default=attr.Factory(lambda: FrozenList(["repodata/repomd.xml"])),
        type=list,
        converter=FrozenList,
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
