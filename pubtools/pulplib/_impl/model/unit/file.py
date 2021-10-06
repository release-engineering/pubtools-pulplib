from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr
from ..convert import frozenlist_or_none_sorted_converter


@unit_type("iso")
@attr.s(kw_only=True, frozen=True)
class FileUnit(Unit):
    """A :class:`~pubtools.pulplib.Unit` representing a generic file.

    .. versionadded:: 1.5.0
    """

    path = pulp_attrib(type=str, pulp_field="name", unit_key=True)
    """Full path for this file in the Pulp repository.

    This may include leading directory components, but
    in the common case, this is only a basename.
    """

    size = pulp_attrib(type=int, converter=int, pulp_field="size", unit_key=True)
    """Size of this file, in bytes."""

    sha256sum = pulp_attrib(
        type=str,
        pulp_field="checksum",
        converter=lambda s: s.lower() if s else s,
        unit_key=True,
    )
    """SHA256 checksum of this file, as a hex string."""

    content_type_id = pulp_attrib(
        default="iso", type=str, pulp_field="_content_type_id"
    )

    repository_memberships = pulp_attrib(
        default=None,
        type=list,
        converter=frozenlist_or_none_sorted_converter,
        pulp_field="repository_memberships",
    )
    """IDs of repositories containing the unit, or ``None`` if this information is unavailable.

    .. versionadded:: 2.6.0
    """

    @size.validator
    def _check_size(self, _, value):
        if value < 0:
            raise ValueError("Not a valid size (must be positive): %s" % value)

    @sha256sum.validator
    def _check_sha256(self, _, value):
        self._check_sum(value, "SHA256", 64)
