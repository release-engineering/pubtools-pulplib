from pubtools.pulplib._impl.criteria import (
    AndCriteria,
    OrCriteria,
    FieldMatchCriteria,
    TrueCriteria,
    RegexMatcher,
    EqMatcher,
    InMatcher,
    ExistsMatcher,
)

from pubtools.pulplib._impl import compat_attr as attr
from pubtools.pulplib._impl.model.attr import PULP2_FIELD, PY_PULP2_CONVERTER


def all_subclasses(klass):
    out = set()
    out.add(klass)
    for subclass in klass.__subclasses__():
        out.update(all_subclasses(subclass))
    return out


def map_field_for_type(field_name, matcher, type_hint):
    if not type_hint:
        return (field_name, matcher)

    attrs_classes = all_subclasses(type_hint)
    attrs_classes = [cls for cls in attrs_classes if attr.has(cls)]
    for klass in attrs_classes:
        # Does the class have this field?
        klass_fields = attr.fields(klass)
        if not hasattr(klass_fields, field_name):
            continue
        field = getattr(klass_fields, field_name)
        metadata = field.metadata
        if PULP2_FIELD in metadata:
            field_name = metadata[PULP2_FIELD]
            converter = metadata.get(PY_PULP2_CONVERTER, lambda x: x)
            return (field_name, matcher._map(converter) if matcher else None)

        # Field was found on the model, but we don't support mapping it to
        # a Pulp field.
        raise NotImplementedError("Searching on field %s is not supported" % field_name)

    # No match => no change, search exactly what was requested
    return (field_name, matcher)


def filters_for_criteria(criteria, type_hint=None):
    # convert a Criteria object to a filters dict as used in the Pulp 2.x API:
    # https://docs.pulpproject.org/dev-guide/conventions/criteria.html#search-criteria
    #
    # type_hint optionally provides the class expected to be found by this search.
    # This can impact the application of certain criteria, e.g. it will affect
    # field mappings looked up by FieldMatchCriteria.
    if criteria is None or isinstance(criteria, TrueCriteria):
        return {}

    if isinstance(criteria, AndCriteria):
        return {"$and": [filters_for_criteria(c) for c in criteria._operands]}

    if isinstance(criteria, OrCriteria):
        return {"$or": [filters_for_criteria(c) for c in criteria._operands]}

    if isinstance(criteria, FieldMatchCriteria):
        field = criteria._field
        matcher = criteria._matcher

        field, matcher = map_field_for_type(field, matcher, type_hint)

        return {field: field_match(matcher)}

    raise TypeError("Not a criteria: %s" % repr(criteria))


def field_match(to_match):
    if isinstance(to_match, RegexMatcher):
        return {"$regex": to_match._pattern}

    if isinstance(to_match, EqMatcher):
        return {"$eq": to_match._value}

    if isinstance(to_match, InMatcher):
        return {"$in": to_match._values}

    if isinstance(to_match, ExistsMatcher):
        return {"$exists": True}

    raise TypeError("Not a matcher: %s" % repr(to_match))
