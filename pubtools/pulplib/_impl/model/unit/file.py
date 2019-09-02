from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr


@unit_type("iso")
@attr.s(kw_only=True, frozen=True)
class FileUnit(Unit):
    """A :class:`~pubtools.pulplib.Unit` representing a generic file.

    .. versionadded:: 1.5.0
    """

    path = pulp_attrib(type=str, pulp_field="name")
    """Full path for this file in the Pulp repository.

    This may include leading directory components, but
    in the common case, this is only a basename.
    """

    size = pulp_attrib(type=int, pulp_field="size")
    """Size of this file, in bytes."""

    sha256sum = pulp_attrib(
        type=str, pulp_field="checksum", converter=lambda s: s.lower() if s else s
    )
    """SHA256 checksum of this file, as a hex string."""

    content_type_id = pulp_attrib(
        default="iso", type=str, pulp_field="_content_type_id"
    )

    @size.validator
    def _check_size(self, _, value):
        if value < 0:
            raise ValueError("Not a valid size (must be positive): %s" % value)

    @sha256sum.validator
    def _check_sha256(self, _, value):
        self._check_sum(value, "SHA256", 64)
