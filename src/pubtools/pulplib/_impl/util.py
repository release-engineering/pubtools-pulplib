ABSENT = object()
SUFFIXES = ("k", "M", "G", "T", "P", "E")


def lookup(value, key, default=ABSENT):
    # look up a key from a dict, supporting nested dicts.
    # This is used as a helper for mongo-like nested lookups as used for
    # certain Pulp fields, e.g. "notes.created" for looking up
    # data["notes"]["created"].
    #
    # If a default is provided, it's returned when the value is absent.
    # Otherwise, KeyError is raised, similar as for a regular dict lookup.
    keys = key.split(".")

    while value and isinstance(value, dict) and keys:
        next_key = keys.pop(0)
        value = value.get(next_key, ABSENT)

    if (value is ABSENT) or keys:
        # it's not present
        if default is ABSENT:
            raise KeyError(key)
        return default

    # it's present
    return value


def dict_put(out, key, value):
    # Put a value into a dict, supporting nested dicts in the case where
    # "key" contains dot-separated subdicts.
    #
    # Example:
    #
    #   data = {}
    #   dict_put(data, "notes.created", "today")
    #   assert data == {"notes": {"created": "today"}}
    #
    # This is the inverse of lookup, and is used while serializing model
    # objects back to Pulp dicts.
    keys = key.split(".")

    while keys:
        next_key = keys.pop(0)
        if not keys:
            # We've got the last key, so we store the value
            out[next_key] = value
        else:
            # Not the last key, so ensure there's a sub-dict.
            out = out.setdefault(next_key, {})


def naturalsize(value):
    """
    Format a number of bytes like a human-readable filesize.
    Uses SI system (metric), so e.g. 10000 B = 10 kB.
    """
    base = 1000

    if isinstance(value, str):
        size_bytes = float(value)
    else:
        size_bytes = value
    abs_bytes = abs(size_bytes)

    if abs_bytes == 1:
        return f"{size_bytes} Byte"
    if abs_bytes < base:
        return f"{int(size_bytes)} Bytes"

    suffix = ""
    for power, suffix in enumerate(SUFFIXES, 2):
        unit = base**power
        if abs_bytes < unit:
            break
    size_natural = base * (size_bytes / unit)
    return f"{size_natural:.1f} {suffix}B"
