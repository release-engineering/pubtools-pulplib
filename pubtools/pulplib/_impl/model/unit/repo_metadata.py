from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr
from ..convert import frozenlist_or_none_sorted_converter


@unit_type("yum_repo_metadata_file")
@attr.s(kw_only=True, frozen=True)
class YumRepoMetadataFileUnit(Unit):
    """A :class:`~pubtools.pulplib.Unit` representing a metadata file in a yum repo.

    .. versionadded:: 2.17.0
    """

    data_type = pulp_attrib(type=str, pulp_field="data_type", unit_key=True)
    """The type of this metadata file, e.g. "productid"."""

    sha256sum = pulp_attrib(
        type=str,
        pulp_field="checksum",
        converter=lambda s: s.lower() if s else s,
        default=None,
    )
    """SHA256 checksum of this metadata file, if known, as a hex string."""

    content_type_id = pulp_attrib(
        default="yum_repo_metadata_file", type=str, pulp_field="_content_type_id"
    )

    repository_memberships = pulp_attrib(
        default=None,
        type=list,
        converter=frozenlist_or_none_sorted_converter,
        pulp_field="repository_memberships",
    )
    """IDs of repositories containing the unit, or ``None`` if this information is unavailable.
    """

    unit_id = pulp_attrib(type=str, pulp_field="_id", default=None)
    """The unique ID of this unit, if known.

    .. versionadded:: 2.20.0
    """
