from .base import Repository, repo_type
from ..attr import pulp_attrib

from pubtools.pulplib._impl import compat_attr as attr


@repo_type("iso-repo")
@attr.s(kw_only=True, frozen=True)
class FileRepository(Repository):
    """A :class:`~pubtools.pulplib.Repository` for generic file distribution."""

    _PUBLISH_DISTRIBUTORS = ["iso_distributor", "cdn_distributor"]

    type = pulp_attrib(default="iso-repo", type=str, pulp_field="notes._repo-type")

    is_sigstore = attr.ib(
        default=attr.Factory(
            lambda self: self.id == "redhat-sigstore", takes_self=True
        ),
        type=bool,
    )

    mutable_urls = attr.ib(default=attr.Factory(lambda: ["PULP_MANIFEST"]), type=list)
