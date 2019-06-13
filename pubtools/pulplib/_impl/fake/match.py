import datetime

from pubtools.pulplib._impl import compat_attr as attr
from pubtools.pulplib._impl.client.errors import PulpException
from pubtools.pulplib._impl.criteria import (
    Criteria,
    TrueCriteria,
    AndCriteria,
    OrCriteria,
    FieldEqCriteria,
    FieldInCriteria,
)
from pubtools.pulplib._impl.model.common import PULP2_FIELD

CLASS_MATCHERS = []


def visit(klass):
    def wrap(func):
        CLASS_MATCHERS.append((klass, func))
        return func

    return wrap


def match_object(criteria, obj):
    for (klass, func) in CLASS_MATCHERS:
        if isinstance(criteria, klass):
            return func(criteria, obj)

    raise TypeError("Unsupported criteria: %s" % repr(criteria))


@visit(TrueCriteria)
def match_true(*_):
    return True


@visit(AndCriteria)
def match_and(criteria, obj):
    if not criteria._operands:
        # real Pulp/mongo rejects this, so should we
        raise PulpException("Invalid AND in search query")
    for subcrit in criteria._operands:
        if not match_object(subcrit, obj):
            return False
    return True


@visit(OrCriteria)
def match_or(criteria, obj):
    if not criteria._operands:
        # real Pulp/mongo rejects this, so should we
        raise PulpException("Invalid OR in search query")
    for subcrit in criteria._operands:
        if match_object(subcrit, obj):
            return True
    return False


@visit(FieldEqCriteria)
def match_eq(criteria, obj):
    field = criteria._field
    value = criteria._value
    return match_field(obj, field, value)


@visit(FieldInCriteria)
def match_in(criteria, obj):
    field = criteria._field
    value = criteria._value
    for elem in value:
        if match_field(obj, field, elem):
            return True
    return False


def match_field(obj, field, value):
    pulp_dict = {}

    for cls_field in attr.fields(type(obj)):
        pulp_key = cls_field.metadata.get(PULP2_FIELD)
        if pulp_key:
            obj_value = getattr(obj, cls_field.name, None)
            # TODO: will we need to differentiate between "absent" and
            # "present but None"?
            if obj_value is not None:
                pulp_dict[pulp_key] = convert_field_to_pulp(
                    obj, cls_field.name, obj_value
                )

    if field in pulp_dict:
        if value is Criteria.exists:
            return True

        return pulp_dict[field] == value

    return False


def convert_field_to_pulp(obj, field_name, value):
    # Return a value converted from Python representation into the representation
    # expected in Pulp's API.
    # obj - some PulpObject subclass
    # field - some attr.ib name
    # value - the value possibly to convert into Pulp representation

    cls_fields = attr.fields(type(obj))
    cls_field = getattr(cls_fields, field_name)

    if cls_field.type is datetime.datetime and isinstance(value, datetime.datetime):
        # We can convert from datetime back to the ISO8601 timestamp format
        # used within Pulp
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    # no conversion
    return value
