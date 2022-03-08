import datetime
import functools

import six
from frozenlist2 import frozenlist

from .attr import PULP2_PY_CONVERTER

# Work around http://bugs.python.org/issue7980 which is closed "Won't Fix"
# for python2:
#
# If multiple threads in a process do the first call to strptime at once,
# a crash can occur. Calling strptime once at import time will avoid that
# condition.
#
# TODO: remove me when py2 support is dropped
datetime.datetime.strptime("", "")


def get_converter(field, value):
    """Given an attrs target field and an input value from Pulp,
    return a converter function which should be used to convert the Pulp value
    into a Python representation."""

    metadata_converter = field.metadata.get(PULP2_PY_CONVERTER)
    if metadata_converter:
        # explicitly defined for this field, just return it
        return metadata_converter

    # Nothing explicitly defined, but check the types, there may still be
    # some applicable default
    if field.type is datetime.datetime and isinstance(value, six.string_types):
        return read_timestamp

    return null_convert


def null_convert(value):
    return value


def read_timestamp(value):
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        # irritatingly (probably a bug), some values were missing the "Z"
        # technically meaning we don't know the timezone.
        # So we try parsing again without it and we just assume it's UTC.
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")


def tolerant_timestamp(value):
    # Converter for fields which can accept a timestamp string, but which
    # falls back to returning the input verbatim if conversion fails.
    #
    # Since it tolerates failed conversions, this is intended to be combined
    # with a validator.
    if isinstance(value, six.string_types):
        try:
            return read_timestamp(value)
        except ValueError:
            # Not a timestamp, conversion doesn't happen
            pass

    return value


def write_timestamp(value):
    # defaults to current time if value is None
    if value is None:
        value = datetime.datetime.utcnow()
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def frozenlist_or_none_converter(obj, map_fn=(lambda x: x)):
    if obj is not None:
        return frozenlist(map_fn(obj))
    return None


frozenlist_or_none_sorted_converter = functools.partial(
    frozenlist_or_none_converter, map_fn=lambda x: sorted(set(x))
)
