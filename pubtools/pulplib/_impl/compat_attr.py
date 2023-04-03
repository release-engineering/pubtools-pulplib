import attr

ATTR_VERSION = tuple(int(x) for x in attr.__version__.split(".")[0:2])

# pylint: disable=invalid-name

# Wrappers around attr module to handle some incompatibilities with older versions of the module.


def s(*args, **kwargs):
    # A few features we'd like to use are not available on older attrs
    # versions, so we just silently disable them.
    #
    # Note this means we're technically exporting a different API on
    # older versions of attr, i.e. keywords-only isn't enforced.
    # This isn't ideal, but is mitigated by the fact that any new code
    # using this library will surely not be tested solely using old versions of attr.
    kwargs = kwargs.copy()

    if "slots" not in kwargs:
        # Slotted classes should be used where possible, but there
        # are a few cases where it won't work, so the possibility
        # is left open to disable it via slots=False.
        kwargs["slots"] = True

    if "repr" not in kwargs:
        # We provide our own __repr__ implementation in PulpObject, so
        # don't use the attrs-generated repr by default
        kwargs["repr"] = False

    if "kw_only" in kwargs and ATTR_VERSION < (18, 2):  # pragma: no cover
        # This is only implemented in attrs 18.2 and newer.
        # attr.s() will raise if kw_only is provided in older version of attr.
        del kwargs["kw_only"]

    return attr.s(*args, **kwargs)


if ATTR_VERSION < (18, 1):  # pragma: no cover
    # older attrs version didn't provide this function yet,
    # but it's easily added here.
    def fields_dict(cls):
        out = {}
        for field in attr.fields(cls):
            out[field.name] = field
        return out

else:
    fields_dict = attr.fields_dict


ib = attr.ib
Factory = attr.Factory
fields = attr.fields
evolve = attr.evolve
has = attr.has
validators = attr.validators
NOTHING = attr.NOTHING
