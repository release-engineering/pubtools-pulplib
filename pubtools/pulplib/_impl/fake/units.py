import hashlib
import tempfile

from pubtools.pulplib import FileUnit, RpmUnit

from .rpmlib import get_rpm_header, get_header_fields, get_keys_from_header


def make_unit(type_id, unit_key, content):
    # Obtain a valid unit representing uploaded 'content'.

    if type_id == "iso":
        return make_iso_unit(unit_key)

    if type_id == "rpm":
        return make_rpm_unit(content)

    # It should not be possible to get here via public API.
    #
    # If you see this message, you're probably halfway through implementing
    # something. Well done, you've found the next place you need to update!
    raise NotImplementedError(
        "fake client does not support upload of '%s'" % type_id
    )  # pragma: no cover


def make_iso_unit(unit_key):
    # All needed info is always provided up-front in the unit key.
    return FileUnit(
        path=unit_key["name"], size=unit_key["size"], sha256sum=unit_key["checksum"]
    )


def make_rpm_unit(content):
    # Since the native RPM library is used under the hood here,
    # any old file-like object isn't good enough; it *must* be a real file with
    # a 'fileno' which can be passed into syscalls. So we have to pipe the content
    # into a temporary file before we call into kobo.rpmlib.
    with tempfile.NamedTemporaryFile(suffix="pubtools-pulplib-fake") as f:
        # While we're at it, we can calculate each of the checksum types expected to
        # exist on the unit.
        hashers = {
            "md5sum": hashlib.md5(),
            "sha1sum": hashlib.sha1(),
            "sha256sum": hashlib.sha256(),
        }

        while True:
            chunk = content.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            for hasher in hashers.values():
                hasher.update(chunk)

        sumattrs = {}
        for (sumtype, hasher) in hashers.items():
            sumattrs[sumtype] = hasher.hexdigest()

        # Read all the other attrs out of the RPM header.
        f.flush()
        f.seek(0)
        header = get_rpm_header(f)

    rpmattrs = get_header_fields(
        header, ["name", "version", "release", "arch", "epochnum", "sourcerpm"]
    )

    # Fill in some special cases:
    # This one uses a different name in the unit vs header.
    rpmattrs["epoch"] = str(rpmattrs.pop("epochnum"))

    # This one is derived from multiple headers.
    rpmattrs["signing_key"] = get_keys_from_header(header)
    if rpmattrs["signing_key"]:
        rpmattrs["signing_key"] = rpmattrs["signing_key"].lower()

    # This isn't actually a property of the RPM at all, but something synthesized.
    rpmattrs["filename"] = "{name}-{version}-{release}.{arch}.rpm".format(**rpmattrs)

    rpmattrs.update(sumattrs)

    return RpmUnit(**rpmattrs)
