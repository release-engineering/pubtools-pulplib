import six

try:
    from kobo.rpmlib import (
        get_rpm_header,
        get_header_fields,
        get_keys_from_header,
        parse_evr,
    )
except Exception as ex:  # pragma: no cover, pylint: disable=broad-except
    # Avoid a hard dependency on RPM bindings at import time - delay the crash
    # until we're actually used (if ever).
    #
    # Why: because there's no officially supported method of getting RPM bindings
    # in place by "pip install", making the dependency tricky on some environments.
    # rpm-py-installer can often be used, so we provide that hint as we crash,
    # but it's not appropriate to unconditionally depend on that.
    exception = ex

    def broken(*_args, **_kwargs):
        six.raise_from(
            RuntimeError(
                "kobo.rpmlib is not available\n"
                + "Hint: consider 'pip install rpm-py-installer'"
            ),
            exception,
        )

    get_rpm_header = broken
    get_header_fields = broken
    get_keys_from_header = broken
    parse_evr = broken

__all__ = [
    "get_rpm_header",
    "get_header_fields",
    "get_keys_from_header",
    "get_rpm_requires",
    "get_rpm_provides",
]


def get_rpm_requires(header):
    header_flags_map = {
        "version": "REQUIREVERSION",
        "name": "REQUIRENAME",
        "flags": "REQUIREFLAGS",
    }
    return _get_rpm_deps(header, header_flags_map)


def get_rpm_provides(header):
    header_flags_map = {
        "version": "PROVIDEVERSION",
        "name": "PROVIDENAME",
        "flags": "PROVIDEFLAGS",
    }
    return _get_rpm_deps(header, header_flags_map)


def _get_rpm_deps(header, header_flags_map):
    header_flags = list(header_flags_map.values())
    raw_deps = get_header_fields(header, header_flags)

    names = raw_deps[header_flags_map["name"]]
    versions = raw_deps[header_flags_map["version"]]
    flags = raw_deps[header_flags_map["flags"]]

    deps = []

    for name, evr, flag in zip(names, versions, flags):
        evr = parse_evr(evr, allow_empty_release=True) if evr else {}

        deps_item = {
            "name": name,
            "version": evr.get("version") or None,
            "release": evr.get("release") or None,
            "epoch": "0" if evr.get("epoch") == "" else None,
            "flags": _parse_dep_relation(flag),
        }

        deps.append(deps_item)

    return deps


def _parse_dep_relation(flag):
    LT = 0x02
    GT = 0x04
    EQ = 0x08

    if flag & LT and flag & EQ:
        flag_str = "LE"
    elif flag & GT and flag & EQ:
        flag_str = "GE"
    elif flag & LT:
        flag_str = "LT"
    elif flag & GT:
        flag_str = "GT"
    elif flag & EQ:
        flag_str = "EQ"
    else:
        flag_str = None

    return flag_str
