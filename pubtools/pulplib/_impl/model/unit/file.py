import datetime

from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr
from ..convert import frozenlist_or_none_sorted_converter
from ..validate import optional_str, instance_of


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

    description = pulp_attrib(
        type=str,
        pulp_field="pulp_user_metadata.description",
        default=None,
        validator=optional_str,
    )
    """A user-oriented terse description of this file.

    This field is **mutable** and may be set by
    :meth:`~FileRepository.upload_file` or
    :meth:`~Client.update_content`.

    .. versionadded:: 2.20.0
    """

    cdn_path = pulp_attrib(
        type=str,
        pulp_field="pulp_user_metadata.cdn_path",
        default=None,
        validator=optional_str,
    )
    """A path, relative to the CDN root, from which this file can be downloaded
    once published.

    This path will not point to any specific repository. However, the file must
    have been published via at least one repository before this path can be
    accessed.

    This field is **mutable** and may be set by
    :meth:`~FileRepository.upload_file` or
    :meth:`~Client.update_content`.

    .. versionadded:: 2.20.0
    """

    cdn_published = pulp_attrib(
        type=datetime.datetime,
        pulp_field="pulp_user_metadata.cdn_published",
        default=None,
        validator=instance_of((datetime.datetime, type(None))),
    )
    """Approximate :class:`~datetime.datetime` in UTC at which this file first
    became available at ``cdn_path``, or ``None`` if this information is
    unavailable.

    This field is **mutable** and may be set by
    :meth:`~FileRepository.upload_file` or
    :meth:`~Client.update_content`.

    .. versionadded:: 2.20.0
    """

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

    unit_id = pulp_attrib(type=str, pulp_field="_id", default=None)
    """The unique ID of this unit, if known.

    .. versionadded:: 2.20.0
    """

    @size.validator
    def _check_size(self, _, value):
        if value < 0:
            raise ValueError("Not a valid size (must be positive): %s" % value)

    @sha256sum.validator
    def _check_sha256(self, _, value):
        self._check_sum(value, "SHA256", 64)
