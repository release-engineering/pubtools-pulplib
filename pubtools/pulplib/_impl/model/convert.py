import datetime
import functools

from frozenlist2 import frozenlist
from frozendict.core import frozendict  # pylint: disable=no-name-in-module

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
    if field.type is datetime.datetime and isinstance(value, str):
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
    if isinstance(value, str):
        try:
            return read_timestamp(value)
        except ValueError:
            # Not a timestamp, conversion doesn't happen
            pass

    return value


def timestamp_converter(value):
    # Converter for fields which are stored as strings,
    # but which model is expecting datetime
    # falls back to returning the input verbatim if not a datetime.
    #
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

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


def frozendict_or_none_converter(obj):
    # Convert object and values to immutable structures.
    # Skip convert if the obj is already frozendict.
    # This happens when the class containing the value is copied (e.g: with attr.evolve).
    if obj is not None and not isinstance(obj, frozendict):
        for (key, value) in obj.items():
            if isinstance(value, list):
                obj[key] = frozenlist_or_none_converter(value)
            if isinstance(value, dict):
                obj[key] = frozendict_or_none_converter(value)
        return frozendict(obj)
    return obj


def freeze(obj):
    """Convert complex object composed of dicts and lists to equivalent object composed of
    frozendicts and frozenlists.
    """

    ret = [None]
    stack = [(obj, ret, 0)]
    traversal = []

    # interate over the structure and do post-order traversal
    while stack:
        cobj, cparent, ckey = stack.pop(0)

        # cobj_replacement represents unfrozen object. This way it's possible to freeze
        # already frozen or partially frozen structure
        cobj_replacement = cobj
        if isinstance(cobj, frozenlist):
            cobj_replacement = [None] * len(cobj)
        if isinstance(cobj, frozendict):
            cobj_replacement = {}

        if isinstance(cobj_replacement, list):
            for nth, i in enumerate(cobj):
                stack.insert(0, (i, cobj_replacement, nth))
        elif isinstance(cobj_replacement, dict):
            for key in cobj:
                stack.insert(0, (cobj[key], cobj_replacement, key))
        traversal.insert(0, (cobj_replacement, cparent, ckey))

    # Walk through traversal record. As traversal is post-order
    # leafs are processed first and therefore nested dict/lists
    # are replaced froze first
    for titem in traversal:
        cobj, cparent, ckey = titem
        # if traversal entry is list replace it with frozenlist
        if isinstance(cobj, list):
            cparent[ckey] = frozenlist(cobj)
        # if traversal entry is list replace it with frozendict
        elif isinstance(cobj, dict):
            cparent[ckey] = frozendict(cobj)
        else:
            cparent[ckey] = cobj

    # return firt items of last object in traversal, which is ret[0].
    return traversal[-1][1][0]


def freeze_or_empty(obj):
    if obj is None:
        return frozenlist([])
    return freeze(obj)
