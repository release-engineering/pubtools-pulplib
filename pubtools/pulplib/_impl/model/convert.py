import datetime

import six

from .attr import PULP2_PY_CONVERTER


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
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def write_timestamp(value):
    # defaults to current time if value is None
    if value is None:
        value = datetime.datetime.utcnow()
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")
