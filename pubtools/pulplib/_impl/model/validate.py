import six

from ..compat_attr import validators

instance_of = validators.instance_of

optional_str = instance_of(six.string_types + (type(None),))
optional_bool = instance_of((bool, type(None)))

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


def optional_list_of(elem_types):
    return OptionalListValidator(instance_of(elem_types))
