import datetime
import re

from pubtools.pulplib._impl import compat_attr as attr
from pubtools.pulplib._impl.client.errors import PulpException
from pubtools.pulplib._impl.client.search import map_field_for_type
from pubtools.pulplib._impl.criteria import (
    TrueCriteria,
    AndCriteria,
    OrCriteria,
    FieldMatchCriteria,
    EqMatcher,
    InMatcher,
    RegexMatcher,
    ExistsMatcher,
    LessThanMatcher,
)
from pubtools.pulplib._impl.model.common import PULP2_FIELD

ABSENT = object()
CLASS_MATCHERS = []


def visit(klass):
    def wrap(func):
        CLASS_MATCHERS.append((klass, func))
        return func

    return wrap


def match_object(*args, **kwargs):  # pylint:disable=inconsistent-return-statements
    dispatch = args[0]
    for (klass, func) in CLASS_MATCHERS:
        if isinstance(dispatch, klass):
            return func(*args, **kwargs)


def get_field(field, obj):
    # Obtain a named field from a model object;
    # 'field' may be either a field name used in Pulp or a field name used
    # by our model.

    # Determine whether this field name refers to a field on the model.
    # Note that we don't care about conversion on the matcher here because:
    # - If it's a field on the model, no conversion is needed since we already
    #   are storing plain objects from the model
    # - If it's a Pulp field, conversion will be handled in pulp_value
    using_model_field = map_field_for_type(field, matcher=None, type_hint=obj.__class__)

    # Are we looking for a field on our model, or a raw Pulp field?
    if using_model_field:
        # If matching a field on the model, we can simply grab and compare
        # the attribute directly.
        return getattr(obj, field, ABSENT)

    # Otherwise, the user passed a Pulp field name (e.g. notes.eng_product_id).
    # Then we delegate to pulp_value, which can look up the corresponding model
    # field and do conversions.
    return pulp_value(field, obj)


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


@visit(FieldMatchCriteria)
def match_field(criteria, obj):
    field = criteria._field
    matcher = criteria._matcher
    return match_object(matcher, field, obj)


@visit(EqMatcher)
def match_field_eq(matcher, field, obj):
    value = get_field(field, obj)
    return value == matcher._value


@visit(RegexMatcher)
def match_field_regex(matcher, field, obj):
    value = get_field(field, obj)
    if value is ABSENT:
        return False
    return re.search(matcher._pattern, value)


@visit(ExistsMatcher)
def match_field_exists(_matcher, field, obj):
    value = get_field(field, obj)
    return value not in [ABSENT, None]


@visit(InMatcher)
def match_in(matcher, field, obj):
    value = get_field(field, obj)
    for elem in matcher._values:
        if elem == value:
            return True
    return False


@visit(LessThanMatcher)
def match_field_less(matcher, field, obj):
    value = get_field(field, obj)
    return value < matcher._value


def pulp_value(pulp_field, obj):
    # Given a Pulp 'field' name and a PulpObject instance,
    # returns the value on the object corresponding to that Pulp field.
    # e.g. if field is 'notes.relative_url', will return obj.relative_url.
    pulp_dict = {}

    for cls_field in attr.fields(type(obj)):
        pulp_key = cls_field.metadata.get(PULP2_FIELD)
        if pulp_key:
            obj_value = getattr(obj, cls_field.name, None)
            # TODO: will we need to differentiate between "absent" and
            # "present but None"? There is no way to tell here if
            # obj_value was explicitly set to None, or if it defaulted
            # to None when the object was constructed.
            if obj_value is not None:
                pulp_dict[pulp_key] = convert_field_to_pulp(
                    obj, cls_field.name, obj_value
                )

    return pulp_dict.get(pulp_field, ABSENT)


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
