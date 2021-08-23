from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr
from ..frozenlist import frozenlist_or_none_sorted_converter


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

    name = pulp_attrib(type=str, pulp_field="name")
    """The name of this RPM.

    Example: the name of bash-5.0.7-1.fc30.x86_64.rpm is "bash".
    """

    version = pulp_attrib(type=str, pulp_field="version")
    """The version of this RPM.

    Example: the version of bash-5.0.7-1.fc30.x86_64.rpm is "5.0.7".
    """

    release = pulp_attrib(type=str, pulp_field="release")
    """The release of this RPM.

    Example: the release of bash-5.0.7-1.fc30.x86_64.rpm is "1.fc30".
    """

    arch = pulp_attrib(type=str, pulp_field="arch")
    """The architecture of this RPM.

    Example: the arch of bash-5.0.7-1.fc30.x86_64.rpm is "x86_64".
    """

    epoch = pulp_attrib(default="0", type=str, pulp_field="epoch")
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
    )
    """SHA256 checksum of this RPM, as a hex string."""

    content_type_id = pulp_attrib(
        default="rpm", type=str, pulp_field="_content_type_id"
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

    @md5sum.validator
    def _check_md5(self, _, value):
        self._check_sum(value, "MD5", 32)

    @sha1sum.validator
    def _check_sha1(self, _, value):
        self._check_sum(value, "SHA1", 40)

    @sha256sum.validator
    def _check_sha256(self, _, value):
        self._check_sum(value, "SHA256", 64)
