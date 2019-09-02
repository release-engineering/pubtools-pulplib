from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr


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
        pulp_field="checksums.sha256",
        converter=lambda s: s.lower() if s else s,
    )
    """SHA256 checksum of this RPM, as a hex string."""

    content_type_id = pulp_attrib(
        default="rpm", type=str, pulp_field="_content_type_id"
    )

    @md5sum.validator
    def _check_md5(self, _, value):
        self._check_sum(value, "MD5", 32)

    @sha1sum.validator
    def _check_sha1(self, _, value):
        self._check_sum(value, "SHA1", 40)

    @sha256sum.validator
    def _check_sha256(self, _, value):
        self._check_sum(value, "SHA256", 64)
