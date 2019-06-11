ABSENT = object()


def lookup(value, key, default=ABSENT):
    keys = key.split(".")

    while value and value is not ABSENT and keys:
        next_key = keys.pop(0)
        value = value.get(next_key) or ABSENT

    if (value is ABSENT) or keys:
        # it's not present
        if default is ABSENT:
            raise KeyError(key)
        return default

    # it's present
    return value
