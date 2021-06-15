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

    Default is to 2.
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
    """Version of ubi config that should be used for population of this repository"""

    def get_binary_repository(self):
        """Returns related binary repository to this repository based on relative url
        or Future[None], if repository is not found"""
        return self._get_related_repository(repo_t="binary")

    def get_debug_repository(self):
        """Returns related debug repository to this repository based on relative url
        or Future[None], if repository is not found"""
        return self._get_related_repository(repo_t="debug")

    def get_source_repository(self):
        """Returns related source repository to this repository based on relative url
        or Future[None], if repository is not found"""
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
