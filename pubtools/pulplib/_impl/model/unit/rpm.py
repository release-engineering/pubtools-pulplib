import datetime

from pubtools.pulplib._impl.model.validate import optional_list_of
from .base import Unit, unit_type, schemaless_init

from ..attr import pulp_attrib
from ... import compat_attr as attr
from ..convert import frozenlist_or_none_converter, frozenlist_or_none_sorted_converter
from ..validate import optional_str, instance_of


@attr.s(kw_only=True, frozen=True)
class RpmDependency(object):
    """
    An RPM dependency entry within :meth:`~RpmUnit.requires` and :meth:`~RpmUnit.provides`.
    """

    name = pulp_attrib(default=None, type=str, pulp_field="name")
    """
    A name of dependency - it can be name of rpm package, shared library, scriplet or 
    another name of dependency.
    """

    version = pulp_attrib(default=None, type=str, pulp_field="version")
    """
    Version of this RPM dependency.
    """

    release = pulp_attrib(default=None, type=str, pulp_field="release")
    """
    Release of this RPM dependency.
    """

    epoch = pulp_attrib(default=None, type=str, pulp_field="epoch")
    """
    Epoch of this RPM dependency.
    """

    flags = pulp_attrib(default=None, type=str, pulp_field="flags")
    """
    Flags representing relation to version of this RPM dependency.
    Can be one of GT (greater than), EQ (equal), LT (less than), GE (greater than or equal) and
    LE (less than or equal).
    """

    @classmethod
    def _from_data(cls, data):
        # Convert from raw list/dict as provided in Pulp responses into model.
        if isinstance(data, list):
            return [cls._from_data(elem) for elem in data]

        return schemaless_init(cls, data)


# Note: Pulp2 models RPM and SRPM as separate unit types,
# but there's actually no difference between their fields at all.
# This separation doesn't seem useful, so we let one class handle both.
@unit_type("rpm")
@unit_type("srpm")
@attr.s(kw_only=True, frozen=True)
class RpmUnit(Unit):
    """A :class:`~pubtools.pulplib.Unit` representing an RPM.

    .. versionadded:: 1.5.0
    """

    name = pulp_attrib(type=str, pulp_field="name", unit_key=True)
    """The name of this RPM.

    Example: the name of bash-5.0.7-1.fc30.x86_64.rpm is "bash".
    """

    version = pulp_attrib(type=str, pulp_field="version", unit_key=True)
    """The version of this RPM.

    Example: the version of bash-5.0.7-1.fc30.x86_64.rpm is "5.0.7".
    """

    release = pulp_attrib(type=str, pulp_field="release", unit_key=True)
    """The release of this RPM.

    Example: the release of bash-5.0.7-1.fc30.x86_64.rpm is "1.fc30".
    """

    arch = pulp_attrib(type=str, pulp_field="arch", unit_key=True)
    """The architecture of this RPM.

    Example: the arch of bash-5.0.7-1.fc30.x86_64.rpm is "x86_64".
    """

    epoch = pulp_attrib(default="0", type=str, pulp_field="epoch", unit_key=True)
    """The epoch of this RPM (most commonly "0").

    Example: the epoch of 3:bash-5.0.7-1.fc30.x86_64.rpm is "3".
    """

    signing_key = pulp_attrib(default=None, type=str, pulp_field="signing_key")
    """The short ID of the GPG key used to sign this RPM.

    .. seealso::
        :meth:`~pubtools.pulplib.Repository.signing_keys`
    """

    filename = pulp_attrib(default=None, type=str, pulp_field="filename")
    """Filename of this RPM.
    
    Example: mod_security_crs-3.3.0-2.el8.noarch.rpm
    """

    sourcerpm = pulp_attrib(default=None, type=str, pulp_field="sourcerpm")
    """Source rpm filename if package is not source package.

    Example: gnu-efi-3.0c-1.1.src.rpm.
    """

    # Checksums:
    # Note that "checksums" isn't part of the unit key, hence why these fields
    # are allowed to be omitted.
    md5sum = pulp_attrib(
        default=None,
        type=str,
        pulp_field="checksums.md5",
        converter=lambda s: s.lower() if s else s,
    )
    """MD5 checksum of this RPM, as a hex string."""

    sha1sum = pulp_attrib(
        default=None,
        type=str,
        pulp_field="checksums.sha1",
        converter=lambda s: s.lower() if s else s,
    )
    """SHA1 checksum of this RPM, as a hex string."""

    sha256sum = pulp_attrib(
        default=None,
        type=str,
        # Use 'checksum' field because it's indexed and therefore much faster than
        # searching for checksums.sha256.
        # It's safe since this is always stored as a copy of the sha256 checksum, see:
        # https://github.com/pulp/pulp_rpm/blob/69759d0fb9a16c0a47b1f49c78f6712e650912e1/plugins/pulp_rpm/plugins/importers/yum/upload.py#L436
        pulp_field="checksum",
        converter=lambda s: s.lower() if s else s,
        unit_key=True,
    )
    """SHA256 checksum of this RPM, as a hex string."""

    content_type_id = pulp_attrib(
        default="rpm", type=str, pulp_field="_content_type_id"
    )

    cdn_path = pulp_attrib(
        type=str,
        pulp_field="pulp_user_metadata.cdn_path",
        default=None,
        validator=optional_str,
    )
    """A path, relative to the CDN root, from which this RPM can be downloaded
    once published.

    This path will not point to any specific repository. However, the RPM must
    have been published via at least one repository before this path can be
    accessed.

    This field is **mutable** and may be set by
    :meth:`~YumRepository.upload_rpm` or
    :meth:`~Client.update_content`.

    .. versionadded:: 2.20.0
    """

    cdn_published = pulp_attrib(
        type=datetime.datetime,
        pulp_field="pulp_user_metadata.cdn_published",
        default=None,
        validator=instance_of((datetime.datetime, type(None))),
    )
    """Approximate :class:`~datetime.datetime` in UTC at which this RPM first
    became available at ``cdn_path``, or ``None`` if this information is
    unavailable.

    This field is **mutable** and may be set by
    :meth:`~YumRepository.upload_rpm` or
    :meth:`~Client.update_content`.

    .. versionadded:: 2.20.0
    """

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

    requires = pulp_attrib(
        default=None,
        type=list,
        converter=frozenlist_or_none_converter,
        pulp_field="requires",
        validator=optional_list_of(RpmDependency),
        pulp_py_converter=RpmDependency._from_data,
    )
    """
    List of dependencies that this RPM requires or ``None`` if this information is unavailable.
    """

    provides = pulp_attrib(
        default=None,
        type=list,
        converter=frozenlist_or_none_converter,
        pulp_field="provides",
        validator=optional_list_of(RpmDependency),
        pulp_py_converter=RpmDependency._from_data,
    )
    """
    List of capabilities that this RPM provides or ``None`` if this information is unavailable.
    """

    @md5sum.validator
    def _check_md5(self, _, value):
        self._check_sum(value, "MD5", 32)

    @sha1sum.validator
    def _check_sha1(self, _, value):
        self._check_sum(value, "SHA1", 40)

    @sha256sum.validator
    def _check_sha256(self, _, value):
        self._check_sum(value, "SHA256", 64)
