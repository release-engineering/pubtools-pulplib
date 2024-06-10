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


validators = attr.validators

if ATTR_VERSION < (19, 1):  # pragma: no cover
    # Backport is_callable, deep_iterable and deep_mapping methods needed elsewhere
    # for use with older attrs version
    @s(repr=False, slots=False, hash=True)
    class _IsCallableValidator:
        def __call__(self, _inst, attr_, value):
            if not callable(value):
                message = (
                    "'{name}' must be callable (got {value!r} that is a {actual!r})."
                )
                raise TypeError(
                    msg=message.format(
                        name=attr_.name, value=value, actual=value.__class__
                    ),
                    value=value,
                )

        def __repr__(self):
            return "<is_callable validator>"

    def is_callable():
        return _IsCallableValidator()

    @s(repr=False, slots=True, hash=True)
    class _DeepIterable:
        member_validator = attr.ib(validator=is_callable())
        iterable_validator = attr.ib(
            default=None, validator=validators.optional(is_callable())
        )

        def __call__(self, inst, attr_, value):
            # pylint: disable=not-callable
            if self.iterable_validator is not None:
                self.iterable_validator(inst, attr_, value)

            for member in value:
                self.member_validator(inst, attr_, member)
            # pylint: enable=not-callable

        def __repr__(self):
            iterable_identifier = (
                ""
                if self.iterable_validator is None
                else f" {self.iterable_validator!r}"
            )
            return (
                f"<deep_iterable validator for{iterable_identifier}"
                f" iterables of {self.member_validator!r}>"
            )

    def deep_iterable(member_validator, iterable_validator=None):
        if isinstance(member_validator, (list, tuple)):
            member_validator = validators.and_(*member_validator)
        return _DeepIterable(member_validator, iterable_validator)

    @s(repr=False, slots=True, hash=True)
    class _DeepMapping:
        key_validator = attr.ib(validator=is_callable())
        value_validator = attr.ib(validator=is_callable())
        mapping_validator = attr.ib(
            default=None, validator=validators.optional(is_callable())
        )

        def __call__(self, inst, attr_, value):
            # pylint: disable=not-callable
            if self.mapping_validator is not None:
                self.mapping_validator(inst, attr_, value)

            for key in value:
                self.key_validator(inst, attr_, key)
                self.value_validator(inst, attr_, value[key])
            # pylint: enable=not-callable

        def __repr__(self):
            return (
                f"<deep_mapping validator for objects mapping {self.key_validator!r} "
                f"to {self.value_validator!r}>"
            )

    def deep_mapping(key_validator, value_validator, mapping_validator=None):
        return _DeepMapping(key_validator, value_validator, mapping_validator)

    validators.is_callable = is_callable
    validators.deep_iterable = deep_iterable
    validators.deep_mapping = deep_mapping


ib = attr.ib
Factory = attr.Factory
fields = attr.fields
evolve = attr.evolve
has = attr.has
NOTHING = attr.NOTHING
