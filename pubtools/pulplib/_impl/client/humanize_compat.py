# Provide a simple fallback for humanize.naturalsize in
# certain legacy environments.
#
# TODO: remove me once py2 support goes away.

# pylint: disable=broad-except


def fallback_naturalsize(value):
    return "%.1f MB" % (float(value) / 1024 / 1024)


try:
    from humanize import naturalsize
except Exception:  # pragma: no cover
    naturalsize = fallback_naturalsize

__all__ = ["naturalsize"]
