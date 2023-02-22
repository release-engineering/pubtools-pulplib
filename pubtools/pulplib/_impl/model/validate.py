from frozenlist2 import frozenlist

from frozendict.core import frozendict  # pylint: disable=no-name-in-module
from ..compat_attr import validators, s, ib

instance_of = validators.instance_of

optional_str = instance_of((str,) + (type(None),))
optional_bool = instance_of((bool, type(None)))
optional_dict = instance_of((dict, type(None)))
optional_frozendict = instance_of((frozendict, type(None)))

# This is a workaround for the absence of deep_iterable on older attr.
# Drop it when the legacy environment is no longer required.
class OptionalListValidator(object):
    def __init__(self, member_validator):
        self.list_validator = instance_of(list)
        self.member_validator = member_validator

    def __call__(self, inst, attr, value):
        if value is None:
            # OK, no more validation
            return

        # We have a non-None value - it should be a list
        self.list_validator(inst, attr, value)

        # Validate every element
        for elem in value:
            self.member_validator(inst, attr, elem)


@s(frozen=True, slots=True, hash=True)
class NamedMappingValidator:
    mapping = ib(
        validator=validators.deep_mapping(
            value_validator=validators.is_callable(),
            key_validator=validators.instance_of(str),
        ),
        factory=dict,
    )
    type_ = ib(default=dict)

    def __call__(self, inst, attr, value):
        validators.instance_of(self.type_)(inst, attr, value)
        extra_values = set(value.keys() - self.mapping.keys())  # pylint: disable=E1101
        missing_values = set(
            self.mapping.keys() - value.keys()  # pylint: disable=E1101
        )  # pylint: disable=E1101
        if extra_values:
            raise ValueError(
                "Mapping {name} contains extra values {extra}".format(
                    name=attr.name, extra=extra_values
                )
            )
        if missing_values:
            raise ValueError(
                "Mapping {name} contains extra values {missing}".format(
                    name=attr.name, missing=missing_values
                )
            )

        for key, val in value.items():
            self.mapping[key](inst, attr, val)  # pylint: disable=E1136


def frozen_named_mapping_validator(mapping):
    return NamedMappingValidator(mapping, frozendict)


@s(kw_only=True, frozen=True, slots=True)
class ContainerListValidator(object):
    def __call__(self, inst, attr, value):
        validators.instance_of(frozenlist)(inst, attr, value)
        validators.deep_iterable(
            validators.and_(
                validators.instance_of(frozendict),
                validators.deep_mapping(
                    key_validator=validators.instance_of(str),
                    value_validator=frozen_named_mapping_validator(
                        {
                            "digest": validators.instance_of(str),
                            "images": validators.deep_mapping(
                                key_validator=validators.instance_of(str),
                                value_validator=validators.deep_mapping(
                                    key_validator=validators.instance_of(str),
                                    value_validator=validators.optional(
                                        validators.instance_of(str)
                                    ),
                                ),
                            ),
                        }
                    ),
                ),
            ),
            iterable_validator=validators.instance_of(frozenlist),
        )(inst, attr, value)


def container_list_validator():
    return ContainerListValidator()


def optional_list_of(elem_types):
    return OptionalListValidator(instance_of(elem_types))
