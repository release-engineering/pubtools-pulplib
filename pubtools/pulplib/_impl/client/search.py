import logging
import datetime
import contextlib
from pubtools.pulplib._impl.criteria import (
    AndCriteria,
    OrCriteria,
    FieldMatchCriteria,
    TrueCriteria,
    RegexMatcher,
    EqMatcher,
    InMatcher,
    ExistsMatcher,
    LessThanMatcher,
)

from pubtools.pulplib._impl import compat_attr as attr
from pubtools.pulplib._impl.model.attr import PULP2_FIELD, PY_PULP2_CONVERTER
from pubtools.pulplib._impl.model.unit.base import Unit

LOG = logging.getLogger("pubtools.pulplib")


def all_subclasses(klass):
    out = set()
    out.add(klass)
    for subclass in klass.__subclasses__():
        out.update(all_subclasses(subclass))
    return out


def to_mongo_json(value):
    # Return a value converted to the format expected for a mongo JSON
    # expression. Only a handful of special types need explicit conversions.
    if isinstance(value, datetime.datetime):
        return {"$date": value.strftime("%Y-%m-%dT%H:%M:%SZ")}

    if isinstance(value, (list, tuple)):
        return [to_mongo_json(elem) for elem in value]

    if isinstance(value, dict):
        out = {}
        for (key, val) in value.items():
            out[key] = to_mongo_json(val)
        return out

    return value


def map_field_for_type(field_name, matcher, type_hint):
    if not type_hint:
        return None

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
    return None


@attr.s
class PulpSearch(object):
    # Helper class representing a prepared Pulp search.
    # Usually just a filters dict, but may include type_ids
    # for unit searches.
    filters = attr.ib(type=dict)
    type_ids = attr.ib(type=list, default=None)


class TypeIdAccumulator(object):
    def __init__(self):
        self.can_accumulate = True
        self.values = []

    def accumulate_from_match(self, match_expr):
        # Are we still in a state where accumulation is possible?
        if not self.can_accumulate:
            raise ValueError(
                (
                    "Can't serialize criteria for Pulp query; too complicated. "
                    "Try simplifying the query with respect to content_type_id."
                )
            )

        # OK, we can accumulate if it's a supported expression type.
        if isinstance(match_expr, dict) and list(match_expr.keys()) == ["$eq"]:
            self.values = [match_expr["$eq"]]
        elif isinstance(match_expr, dict) and list(match_expr.keys()) == ["$in"]:
            self.values = match_expr["$in"]
        else:
            raise ValueError(
                (
                    "Can't serialize criteria for Pulp query, "
                    "unsupported expression for content_type_id: %s\n"
                )
                % repr(match_expr)
            )

        # It is only possible to accumulate once.
        self.can_accumulate = False

    @property
    @contextlib.contextmanager
    def no_accumulate(self):
        old_can_accumulate = self.can_accumulate
        self.can_accumulate = False
        try:
            yield
        finally:
            self.can_accumulate = old_can_accumulate


def search_for_criteria(criteria, type_hint=None, type_ids_accum=None):
    # convert a Criteria object to a PulpSearch with filters as used in the Pulp 2.x API:
    # https://docs.pulpproject.org/dev-guide/conventions/criteria.html#search-criteria
    #
    # type_hint optionally provides the class expected to be found by this search.
    # This can impact the application of certain criteria, e.g. it will affect
    # field mappings looked up by FieldMatchCriteria.
    if criteria is None or isinstance(criteria, TrueCriteria):
        return PulpSearch(filters={})

    type_ids_accum = type_ids_accum or TypeIdAccumulator()

    if isinstance(criteria, AndCriteria):
        clauses = [
            search_for_criteria(c, type_hint, type_ids_accum).filters
            for c in criteria._operands
        ]

        # Empty filters do not affect the result and can be simplified.
        clauses = [c for c in clauses if c != {}]

        # A single clause is the same as no $and at all.
        if len(clauses) == 1:
            filters = clauses[0]
        else:
            filters = {"$and": clauses}

    elif isinstance(criteria, OrCriteria):
        with type_ids_accum.no_accumulate:
            filters = {
                "$or": [
                    search_for_criteria(c, type_hint, type_ids_accum).filters
                    for c in criteria._operands
                ]
            }

    elif isinstance(criteria, FieldMatchCriteria):
        field = criteria._field
        matcher = criteria._matcher

        mapped = map_field_for_type(field, matcher, type_hint)
        if mapped:
            field, matcher = mapped

        match_expr = field_match(matcher)

        # If we are looking at the special _content_type_id field
        # for the purpose of a unit search...
        if field == "_content_type_id" and type_hint is Unit:
            # We should not include this into filters, but instead
            # attempt to accumulate it into type_ids_out.
            # This is because type_ids needs to be serialized into the
            # top-level 'criteria' and not 'filters', and there are
            # additional restrictions on its usage.
            type_ids_accum.accumulate_from_match(match_expr)

            filters = {}
        else:
            filters = {field: match_expr}

    else:
        raise TypeError("Not a criteria: %s" % repr(criteria))

    return PulpSearch(filters=filters, type_ids=type_ids_accum.values[:])


def filters_for_criteria(criteria, type_hint=None):
    return search_for_criteria(criteria, type_hint).filters


def field_match(to_match):
    if isinstance(to_match, RegexMatcher):
        return {"$regex": to_match._pattern}

    if isinstance(to_match, EqMatcher):
        return {"$eq": to_mongo_json(to_match._value)}

    if isinstance(to_match, InMatcher):
        return {"$in": to_mongo_json(to_match._values)}

    if isinstance(to_match, ExistsMatcher):
        return {"$exists": True}

    if isinstance(to_match, LessThanMatcher):
        return {"$lt": to_mongo_json(to_match._value)}

    raise TypeError("Not a matcher: %s" % repr(to_match))
