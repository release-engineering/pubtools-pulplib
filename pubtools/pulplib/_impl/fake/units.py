import hashlib
import tempfile
import logging
import random
import threading
import uuid

import yaml
import attr

from pubtools.pulplib import (
    FileUnit,
    RpmUnit,
    RpmDependency,
    ErratumUnit,
    YumRepoMetadataFileUnit,
    ModulemdUnit,
    ModulemdDependency,
    ModulemdDefaultsUnit,
)

from .rpmlib import (
    get_rpm_header,
    get_header_fields,
    get_keys_from_header,
    get_rpm_requires,
    get_rpm_provides,
)
from ..model.attr import PULP2_UNIT_KEY

LOG = logging.getLogger("pubtools.pulplib")


class UnitMaker(object):
    def __init__(self, seen_unit_ids):
        self._lock = threading.RLock()
        self._uuidgen = random.Random()
        self._uuidgen.seed(0)
        self._seen_unit_ids = seen_unit_ids

    def next_unit_id(self):
        with self._lock:
            while True:
                next_raw_id = self._uuidgen.randint(0, 2**128)
                if next_raw_id not in self._seen_unit_ids:
                    break

        return str(uuid.UUID(int=next_raw_id))

    def make_units(self, type_id, unit_key, unit_metadata, content, repo_id):
        # Obtain valid unit(s) representing uploaded 'content'.
        if type_id == "iso":
            return [self.make_iso_unit(unit_key, unit_metadata)]

        if type_id == "yum_repo_metadata_file":
            return [self.make_yum_repo_metadata_unit(unit_key, unit_metadata)]

        if type_id == "rpm":
            return [self.make_rpm_unit(content, unit_metadata)]

        if type_id == "erratum":
            return [self.make_erratum_unit(unit_metadata)]

        if type_id == "modulemd":
            return self.make_module_units(content, repo_id)

        # Comps-related types are accepted, but we do not actually process
        # them into units.
        if type_id in (
            "package_group",
            "package_langpacks",
            "package_category",
            "package_environment",
        ):
            return []

        # It should not be possible to get here via public API.
        #
        # If you see this message, you're probably halfway through implementing
        # something. Well done, you've found the next place you need to update!
        raise NotImplementedError(
            "fake client does not support upload of '%s'" % type_id
        )  # pragma: no cover

    def make_iso_unit(self, unit_key, unit_metadata):
        usermeta = (unit_metadata or {}).get("pulp_user_metadata") or {}

        return FileUnit(
            unit_id=self.next_unit_id(),
            path=unit_key["name"],
            size=unit_key["size"],
            sha256sum=unit_key["checksum"],
            **usermeta
        )

    def make_yum_repo_metadata_unit(self, unit_key, unit_metadata):
        # For expected fields in unit_key vs metadata, refer to:
        # https://github.com/pulp/pulp_rpm/blob/5c5a7dcc058b29d89b3a913d29cfcab41db96686/plugins/pulp_rpm/plugins/importers/yum/upload.py#L246
        return YumRepoMetadataFileUnit(
            unit_id=self.next_unit_id(),
            data_type=unit_key["data_type"],
            sha256sum=unit_metadata["checksum"],
        )

    def make_erratum_unit(self, metadata):
        md = metadata.copy()
        md["_id"] = self.next_unit_id()
        md["_content_type_id"] = "erratum"
        return ErratumUnit.from_data(md)

    def make_rpm_unit(self, content, unit_metadata):
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
        rpmattrs["filename"] = "{name}-{version}-{release}.{arch}.rpm".format(
            **rpmattrs
        )

        rpmattrs["requires"] = [
            RpmDependency._from_data(item) for item in get_rpm_requires(header)
        ]
        rpmattrs["provides"] = [
            RpmDependency._from_data(item) for item in get_rpm_provides(header)
        ]

        rpmattrs.update(sumattrs)

        usermeta = (unit_metadata or {}).get("pulp_user_metadata") or {}
        rpmattrs.update(usermeta)

        return RpmUnit(unit_id=self.next_unit_id(), **rpmattrs)

    def make_module_units(self, content, repo_id):
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

                dependencies = data.pop("dependencies", None)

                # Pulp does not store entire 'dependencies' but only the 'requires'
                # part, a little bit of parsing is required in the manner similar to pulp
                if dependencies:
                    parsed_deps = []
                    for dep in dependencies:
                        dep_item = {}
                        for k, v in dep["requires"].items():
                            dep_item[k] = v
                        parsed_deps.append(dep_item)

                    attrs["dependencies"] = ModulemdDependency._from_data(parsed_deps)

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
                    "FakeClient ignoring modulemd document of unknown type '%s'",
                    doc_type,
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
            out.append(klass(unit_id=self.next_unit_id(), **attrs))

        return out


def is_erratum_version_newer(old_erratum, new_erratum):
    # A comparison of 'version' field between two erratum units which
    # aims to be compatible with:
    # https://github.com/pulp/pulp_rpm/blob/5c5a7dcc058b29d89b3a913d29cfcab41db96686/plugins/pulp_rpm/yum_plugin/util.py#L196

    old_version = getattr(old_erratum, "version", "")
    new_version = getattr(new_erratum, "version", "")

    if not new_version:
        return False

    try:
        new = float(new_version)

        if not old_version:
            old = 0
        else:
            old = float(old_version)
    except ValueError:
        # non-numeric field means we just treat new_version as newer.
        return True

    return new > old


def merge_units(old_unit, new_unit):
    # Given a unit which already exists in (fake) Pulp and a proposed new
    # unit, returns the new unit which should be stored - potentially
    # merging certain fields with the old unit.

    if old_unit is None:
        # No previous value in pulp
        return new_unit

    repos = None

    # If there's an existing unit, and either old or new unit has some
    # repo memberships, the repo memberships are merged.
    if (
        old_unit.repository_memberships is not None
        or new_unit.repository_memberships is not None
    ):
        repos = set(
            (old_unit.repository_memberships or [])
            + (new_unit.repository_memberships or [])
        )

    # By default, the new unit is used completely and it overwrites any
    # prior unit with the same key (excepting the repository_memberships).
    #
    # There is one special case for erratum units.
    # The new unit is only used if certain fields differ,
    # mainly 'version'. The actual logic is quite a bit more complicated
    # (refer to https://github.com/pulp/pulp_rpm/blob/5c5a7dcc058b29d89b3a913d29cfcab41db96686/plugins/pulp_rpm/plugins/db/models.py#L1233)
    # but our tools only use 'version' field for this, so the other complexity
    # seems not worth reproducing in the fake.
    if old_unit.content_type_id == "erratum" and not is_erratum_version_newer(
        old_unit, new_unit
    ):
        LOG.debug(
            "FakeClient ignoring erratum upload %s due to non-newer version",
            new_unit.id,
        )
        # Upload request is effectively ignored, the old unit is reused,
        # discarding any of the changed fields.
        #
        # Note: real Pulp also has quite complicated logic around 'pkglist'
        # field, we do not currently attempt to reproduce this in the fake.
        new_unit = old_unit

    return attr.evolve(new_unit, unit_id=old_unit.unit_id, repository_memberships=repos)


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

    if isinstance(unit, ErratumUnit):
        return (unit.id,)

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
