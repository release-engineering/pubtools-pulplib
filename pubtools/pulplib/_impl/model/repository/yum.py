from .base import Repository, repo_type
from ..attr import pulp_attrib
from ... import compat_attr as attr


@repo_type("rpm-repo")
@attr.s(kw_only=True, frozen=True)
class YumRepository(Repository):
    """A :class:`~pubtools.pulplib.Repository` for RPMs, errata and related content."""

    # this class only overrides some defaults for attributes defined in super

    type = pulp_attrib(default="rpm-repo", type=str, pulp_field="notes._repo-type")

    mutable_urls = attr.ib(
        default=attr.Factory(lambda: ["repodata/repomd.xml"]), type=list
    )
