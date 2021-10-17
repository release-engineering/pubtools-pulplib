import six

from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr
from ..validate import optional_bool, optional_list_of, optional_str, instance_of
from ..convert import frozenlist_or_none_sorted_converter, frozenlist_or_none_converter


def schemaless_init(cls, data):
    # Construct and return an instance of (attrs-using) cls from
    # pulp data, where data in pulp has no schema at all (and hence
    # every field could possibly be missing).
    kwargs = {}
    for key in [fld.name for fld in attr.fields(cls)]:
        if key in data:
            kwargs[key] = data[key]

    return cls(**kwargs)


@attr.s(kw_only=True, frozen=True)
class ErratumReference(object):
    """A reference within a :meth:`~ErratumUnit.references` list."""

    href = attr.ib(type=str, default=None, validator=optional_str)
    """A URL."""

    id = attr.ib(type=str, default=None, validator=optional_str)
    """A short ID for the reference, unique within this erratum."""

    title = attr.ib(type=str, default=None, validator=optional_str)
    """A title for the reference; analogous to the 'title' attribute
    in HTML.
    """

    type = attr.ib(type=str, default=None, validator=optional_str)
    """Type of reference. This defines the expected target of the URL
    and includes at least:

    - "self": reference to a page for this advisory
    - "bugzilla": reference to a bug
    - "other": any other kind of reference
    """

    @classmethod
    def _from_data(cls, data):
        # Convert from raw list/dict in Pulp response
        if isinstance(data, list):
            return [cls._from_data(elem) for elem in data]

        return schemaless_init(cls, data)


@attr.s(kw_only=True, frozen=True)
class ErratumModule(object):
    """A module entry within a :meth:`~ErratumUnit.pkglist`."""

    name = attr.ib(type=str, default=None, validator=optional_str)
    """Module name."""

    stream = attr.ib(type=str, default=None, validator=optional_str)
    """Module stream."""

    version = attr.ib(type=str, default=None, validator=optional_str)
    """Module version."""

    context = attr.ib(type=str, default=None, validator=optional_str)
    """Module context."""

    arch = attr.ib(type=str, default=None, validator=optional_str)
    """Module architecture."""

    @classmethod
    def _from_data(cls, data):
        return schemaless_init(cls, data)


@attr.s(kw_only=True, frozen=True)
class ErratumPackage(object):
    """A package (RPM) entry within a :meth:`~ErratumUnit.pkglist`."""

    arch = attr.ib(type=str, default=None, validator=optional_str)
    """RPM architecture."""

    filename = attr.ib(type=str, default=None, validator=optional_str)
    """RPM filename (basename)."""

    epoch = attr.ib(type=str, default=None, validator=optional_str)
    """RPM epoch."""

    name = attr.ib(type=str, default=None, validator=optional_str)
    """RPM name (e.g. "bash-4.0.1-1.el7.x86_64.rpm" name is "bash")"""

    version = attr.ib(type=str, default=None, validator=optional_str)
    """RPM version (e.g. "bash-4.0.1-1.el7.x86_64.rpm" version is "4.0.1")"""

    release = attr.ib(type=str, default=None, validator=optional_str)
    """RPM release (e.g. "bash-4.0.1-1.el7.x86_64.rpm" version is "1.el7")"""

    src = attr.ib(type=str, default=None, validator=optional_str)
    """Filename of the source RPM from which this RPM was built; equal to
    :meth:`filename` for the source RPM itself.
    """

    reboot_suggested = attr.ib(type=bool, default=None, validator=optional_bool)
    """True if rebooting host machine is recommended after installing this package."""

    md5sum = attr.ib(type=str, default=None, validator=optional_str)
    """MD5 checksum of this RPM in hex string form, if available."""

    sha1sum = attr.ib(type=str, default=None, validator=optional_str)
    """SHA1 checksum of this RPM in hex string form, if available."""

    sha256sum = attr.ib(type=str, default=None, validator=optional_str)
    """SHA256 checksum of this RPM in hex string form, if available."""

    @classmethod
    def _from_data(cls, data):
        if isinstance(data, list):
            return [cls._from_data(elem) for elem in data]

        data_updated = data.copy()

        # parse the odd 'sum' structure, which is a list of form:
        # [<algo>, <hexdigest>, <algo>, <hexdigest>, ...]
        sums = {}
        raw_sum = data_updated.pop("sum", [])
        while raw_sum:
            sums[raw_sum[0] + "sum"] = raw_sum[1]
            raw_sum = raw_sum[2:]
        data_updated.update(sums)

        return schemaless_init(cls, data_updated)


@attr.s(kw_only=True, frozen=True)
class ErratumPackageCollection(object):
    """A collection of packages found within an :meth:`~ErratumUnit.pkglist`.

    A non-modular advisory typically contains only a single collection, while modular
    advisories typically contain one collection per module.
    """

    name = attr.ib(type=str, default=None, validator=optional_str)
    """A name for this collection. The collection name has no specific meaning,
    but must be unique within an advisory.
    """

    packages = attr.ib(
        type=list,
        default=None,
        converter=frozenlist_or_none_converter,
        validator=optional_list_of(ErratumPackage),
    )
    """List of packages within this collection.

    :type: list[ErratumPackage]
    """

    short = attr.ib(type=str, default=None, validator=optional_str)
    """An alternative name for this collection. In practice, this field
    is typically blank.
    """

    module = attr.ib(
        type=ErratumModule,
        default=None,
        validator=instance_of((ErratumModule, type(None))),
    )
    """An :class:`~ErratumModule` defining the module this entry is associated
    with, if any.
    """

    @classmethod
    def _from_data(cls, data):
        # Convert from raw list/dict as provided in Pulp responses into model.
        if isinstance(data, list):
            return [cls._from_data(elem) for elem in data]

        data_updated = data.copy()

        if "packages" in data:
            data_updated["packages"] = ErratumPackage._from_data(data["packages"])
        if "module" in data:
            data_updated["module"] = ErratumModule._from_data(data["module"])

        return schemaless_init(cls, data_updated)


@unit_type("erratum")
@attr.s(kw_only=True, frozen=True)
class ErratumUnit(Unit):
    """A :class:`~pubtools.pulplib.Unit` representing an erratum/advisory.

    .. versionadded:: 2.17.0
    """

    id = pulp_attrib(type=str, pulp_field="id", unit_key=True, validator=optional_str)
    """The ID of this advisory.

    Example: ``"RHSA-2021:0672"``"""

    version = pulp_attrib(
        type=str, pulp_field="version", default=None, validator=optional_str
    )
    """The version of this advisory.

    Though stored as a string, this field typically takes the form of an
    integer starting at "1" and incremented whenever the advisory is modified.
    """

    status = pulp_attrib(
        type=str, pulp_field="status", default=None, validator=optional_str
    )
    """Status, typically 'final'."""

    updated = pulp_attrib(
        type=str, pulp_field="updated", default=None, validator=optional_str
    )
    """Timestamp of the last update to this advisory.

    Typically of the form '2019-12-31 06:54:41 UTC', but this is not enforced."""

    issued = pulp_attrib(
        type=str, pulp_field="issued", default=None, validator=optional_str
    )
    """Timestamp of the initial release of this advisory.

    Uses the same format as :meth:`updated`."""

    description = pulp_attrib(
        type=str, pulp_field="description", default=None, validator=optional_str
    )
    """Full human-readable description of the advisory, usually multiple lines."""

    pushcount = pulp_attrib(
        type=str, pulp_field="pushcount", default=None, validator=optional_str
    )
    """Number of times advisory has been revised and published (starting at '1')."""

    reboot_suggested = pulp_attrib(
        type=bool, pulp_field="reboot_suggested", default=None, validator=optional_bool
    )
    """True if rebooting host machine is recommended after installing this advisory."""

    from_ = pulp_attrib(
        type=str, pulp_field="from", default=None, validator=optional_str
    )
    """Contact email address for the owner of the advisory.

    Note that the canonical name for this attribute is ``from``.
    As this clashes with a Python keyword, in most contexts the attribute is
    available as an alias, ``from_``.
    """

    rights = pulp_attrib(
        type=str, pulp_field="rights", default=None, validator=optional_str
    )
    """Copyright message."""

    title = pulp_attrib(
        type=str, pulp_field="title", default=None, validator=optional_str
    )
    """Title of the advisory (e.g. 'bash bugfix and enhancement')."""

    severity = pulp_attrib(
        type=str, pulp_field="severity", default=None, validator=optional_str
    )
    """Severity of the advisory, e.g. "low", "moderate", "important" or "critical"."""

    release = pulp_attrib(
        type=str, pulp_field="release", default=None, validator=optional_str
    )
    """Release number. Typically an integer-string, initially "0"."""

    type = pulp_attrib(
        type=str, pulp_field="type", default=None, validator=optional_str
    )
    """"bugfix", "security" or "enhancement"."""

    solution = pulp_attrib(
        type=str, pulp_field="solution", default=None, validator=optional_str
    )
    """Text explaining how to apply the advisory."""

    summary = pulp_attrib(
        type=str, pulp_field="summary", default=None, validator=optional_str
    )
    """Typically a single sentence briefly describing the advisory."""

    content_types = pulp_attrib(
        type=list,
        pulp_field="pulp_user_metadata.content_types",
        converter=frozenlist_or_none_converter,
        default=None,
        validator=optional_list_of(six.string_types),
    )
    """A list of content types associated with the advisory.

    For example, "rpm" may be found in this list if the advisory has any
    associated RPMs.
    """

    references = pulp_attrib(
        type=list,
        pulp_field="references",
        pulp_py_converter=ErratumReference._from_data,
        converter=frozenlist_or_none_converter,
        default=None,
        validator=optional_list_of(ErratumReference),
    )
    """A list of references associated with the advisory."""

    pkglist = pulp_attrib(
        type=list,
        pulp_field="pkglist",
        pulp_py_converter=ErratumPackageCollection._from_data,
        converter=frozenlist_or_none_converter,
        default=None,
        validator=optional_list_of(ErratumPackageCollection),
    )
    """A list of package collections associated with the advisory."""

    content_type_id = pulp_attrib(
        default="erratum", type=str, pulp_field="_content_type_id"
    )

    repository_memberships = pulp_attrib(
        default=None,
        type=list,
        converter=frozenlist_or_none_sorted_converter,
        pulp_field="repository_memberships",
    )
    """IDs of repositories containing the unit, or ``None`` if this information is unavailable.
    """
