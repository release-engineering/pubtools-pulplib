from .base import Repository, SyncOptions, repo_type
from ..frozenlist import FrozenList
from ..attr import pulp_attrib
from ... import compat_attr as attr


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
