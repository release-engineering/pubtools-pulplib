import six

try:
    from kobo.rpmlib import get_rpm_header, get_header_fields, get_keys_from_header
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

__all__ = ["get_rpm_header", "get_header_fields", "get_keys_from_header"]
