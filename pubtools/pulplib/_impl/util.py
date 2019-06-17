ABSENT = object()


def lookup(value, key, default=ABSENT):
    # look up a key from a dict, supporting nested dicts.
    # This is used as a helper for mongo-like nested lookups as used for
    # certain Pulp fields, e.g. "notes.created" for looking up
    # data["notes"]["created"].
    #
    # If a default is provided, it's returned when the value is absent.
    # Otherwise, KeyError is raised, similar as for a regular dict lookup.
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
