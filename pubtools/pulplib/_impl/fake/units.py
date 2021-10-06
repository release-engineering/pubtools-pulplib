import hashlib
import tempfile
import logging

import yaml
import attr

from pubtools.pulplib import (
    FileUnit,
    RpmUnit,
    YumRepoMetadataFileUnit,
    ModulemdUnit,
    ModulemdDefaultsUnit,
)

from .rpmlib import get_rpm_header, get_header_fields, get_keys_from_header
from ..model.attr import PULP2_UNIT_KEY

LOG = logging.getLogger("pubtools.pulplib")


def make_units(type_id, unit_key, unit_metadata, content, repo_id):
    # Obtain valid unit(s) representing uploaded 'content'.

    if type_id == "iso":
        return [make_iso_unit(unit_key)]

    if type_id == "yum_repo_metadata_file":
        return [make_yum_repo_metadata_unit(unit_key, unit_metadata)]

    if type_id == "rpm":
        return [make_rpm_unit(content)]

    if type_id == "modulemd":
        return make_module_units(content, repo_id)

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


def make_yum_repo_metadata_unit(unit_key, unit_metadata):
    # For expected fields in unit_key vs metadata, refer to:
    # https://github.com/pulp/pulp_rpm/blob/5c5a7dcc058b29d89b3a913d29cfcab41db96686/plugins/pulp_rpm/plugins/importers/yum/upload.py#L246
    return YumRepoMetadataFileUnit(
        data_type=unit_key["data_type"], sha256sum=unit_metadata["checksum"]
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


def make_module_units(content, repo_id):
    # Note: consider using libmodulemd here once there is no need for this
    # code to support legacy (pre-RHEL8) environments.
    docs = list(yaml.load_all(content, Loader=yaml.BaseLoader))

    out = []
    for doc in docs:
        attrs = {}

        doc_type = doc.get("document")
        data = doc.get("data") or {}

        if doc_type == "modulemd":
            klass = ModulemdUnit

            # Pulp does not store entire 'artifacts' but only the 'rpms'
            # subkey
            artifacts = data.pop("artifacts", None)
            if artifacts and "rpms" in artifacts:
                attrs["artifacts"] = artifacts["rpms"]

        elif doc_type == "modulemd-defaults":
            klass = ModulemdDefaultsUnit

            # This is always initialized using the repo for which we're uploading.
            attrs["repo_id"] = repo_id

            # For whatever reason, pulp renames this field, so it won't
            # be picked up by the generic attrs<=>unit mapping below.
            if "module" in data:
                attrs["name"] = data["module"]

        else:
            # Pulp silently ignores any unknown document types, so we do the same.
            LOG.debug(
                "FakeClient ignoring modulemd document of unknown type '%s'", doc_type
            )
            continue

        # attr names match the names used in modulemd data, so they can
        # simply be copied across.
        fields = [f.name for f in attr.fields(klass)]
        for field in fields:
            if field in data:
                attrs[field] = data[field]

        # Note: if any mandatory fields are missing, or conversions can't
        # happen, this is where we crash.
        out.append(klass(**attrs))

    return out


def make_unit_key(unit):
    # Given a unit, returns a unit key tuple used internally by the fake client.
    #
    # The unit keys returned here do not have to be precisely identical to those
    # used by a real Pulp server. However, they should be conceptually equivalent.
    # The fake client will keep all references to units via these keys, so the
    # fields used within a key controls whether an upload operation would add a new
    # unit or overwrite an existing one.
    #
    # Example: in Pulp it is not possible to store multiple ISO units with the same
    # (path, checksum, size). The fake client needs to use a unit key incorporating
    # those same fields, otherwise the fake could create situations which are
    # impossible on a real Pulp server.

    if isinstance(unit, FileUnit):
        return (unit.path, unit.sha256sum, unit.size)

    if isinstance(unit, YumRepoMetadataFileUnit):
        # This should not be possible because the unit_key embeds a repo_id.
        # If this somehow occurs, we can't continue.
        assert (
            len(unit.repository_memberships) == 1
        ), "BUG: a YumRepoMetadataFileUnit has been created without any repository!"
        return (unit.data_type, unit.repository_memberships[0])

    if isinstance(unit, RpmUnit):
        return (
            unit.name,
            unit.epoch,
            unit.version,
            unit.release,
            unit.arch,
            unit.sha256sum,
        )

    if isinstance(unit, ModulemdUnit):
        return (unit.nsvca,)

    if isinstance(unit, ModulemdDefaultsUnit):
        return (unit.name, unit.repo_id)

    # Can't get here normally.
    # If you get here, you're probably partway through implementing a new type of unit.
    raise NotImplementedError(
        "fake client does not support '%s'" % unit
    )  # pragma: no cover


def with_key_only(units):
    # Given some units, returns copies of those units with only unit_key
    # fields present; mimics the behavior of pulp when filling units_successful
    # field on tasks.
    out = []
    for unit in units:
        klass = type(unit)
        kwargs = {}
        for field in attr.fields(klass):
            if field.metadata.get(PULP2_UNIT_KEY):
                kwargs[field.name] = getattr(unit, field.name)

        out.append(klass(**kwargs))

    return out
