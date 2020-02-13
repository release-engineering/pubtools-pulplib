from .base import Repository, SyncOptions, repo_type
from ..frozenlist import FrozenList
from ..attr import pulp_attrib
from ... import compat_attr as attr


@attr.s(kw_only=True, frozen=True)
class YumSyncOptions(SyncOptions):
    """Options controlling a container repository
    :meth:`~pubtools.pulplib.YumRepository.sync`.
    """

    query_auth_token = pulp_attrib(default=None, type=str)
    """An authorization token that will be added to every request made to the feed URL's server
    """

    validate = pulp_attrib(default=None, type=bool)
    """If True, checksum of each file will be verified against the metadata's expectation
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

    copy_children = pulp_attrib(default=None, type=bool)
    """when False, will not attempt to locate and copy child packages of errata, groups, or categories
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

    recursive = pulp_attrib(default=None, type=bool)
    """If true, units are copied together with the latest versions of their dependencies
    """

    recursive_conservative = pulp_attrib(default=None, type=bool)
    """If true, units are copied together with their dependencies, unless those are already satisfied by the content in the target repository.
    """

    additional_repos = pulp_attrib(default=None, type=bool)
    """This option allows for dependencies to be found in repositories ouside of the one the specified in the copy command
    """


@repo_type("rpm-repo")
@attr.s(kw_only=True, frozen=True)
class YumRepository(Repository):
    """A :class:`~pubtools.pulplib.Repository` for RPMs, errata and related content."""

    # this class only overrides some defaults for attributes defined in super

    type = pulp_attrib(default="rpm-repo", type=str, pulp_field="notes._repo-type")

    mutable_urls = attr.ib(
        default=attr.Factory(lambda: FrozenList(["repodata/repomd.xml"])),
        type=list,
        converter=FrozenList,
    )
