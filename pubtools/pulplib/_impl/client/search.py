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
    UnitTypeMatchCriteria,
)

from pubtools.pulplib._impl import compat_attr as attr
from pubtools.pulplib._impl.model.attr import PULP2_FIELD, PY_PULP2_CONVERTER
from pubtools.pulplib._impl.model.unit.base import Unit, class_for_type_id
from pubtools.pulplib._impl.client.errors import AmbiguousQueryException

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


def raise_ambiguous_query(field_name, type_hint, grouped_class_names):
    # Raise an exception with a meaningful message in the case where a query
    # can't be executed due to field ambiguity.
    #
    # Example: if searching on field 'version', the caller might be intending
    # to use FileUnit.version or ModulemdUnit.version.
    # This message will point out the ambiguity and suggest how to resolve
    # the problem.

    message = ["Field '%s' is ambiguous." % field_name]
    message.append(
        "A subtype of %s must be provided to select one of the following groups:"
        % type_hint.__name__
    )
    field_lines = []
    for class_names in grouped_class_names:
        field_names = ["%s.%s" % (name, field_name) for name in sorted(class_names)]
        field_lines.append("  " + ", ".join(field_names))
    field_lines.sort()
    message.extend(field_lines)
    raise AmbiguousQueryException("\n".join(message))


def map_field_for_type(field_name, matcher, type_hint):
    if not type_hint:
        return None

    attrs_classes = all_subclasses(type_hint)
    attrs_classes = [cls for cls in attrs_classes if attr.has(cls)]
    found = {}
    for klass in attrs_classes:
        # Does the class have this field?
        klass_fields = attr.fields(klass)
        if not hasattr(klass_fields, field_name):
            continue
        field = getattr(klass_fields, field_name)
        metadata = field.metadata
        if PULP2_FIELD in metadata:
            pulp_field_name = metadata[PULP2_FIELD]
            converter = metadata.get(PY_PULP2_CONVERTER, lambda x: x)
            mapped = matcher._map(converter) if matcher else None
            key = (pulp_field_name, mapped)
            found.setdefault(key, []).append(klass.__name__)
            continue

        # Field was found on the model, but we don't support mapping it to
        # a Pulp field.
        raise NotImplementedError("Searching on field %s is not supported" % field_name)

    if len(found) == 1:
        # Found exactly one definition => great, use it
        return list(found.keys())[0]

    if len(found) > 1:
        # Found multiple definitions => a problem, we don't know what to use.
        return raise_ambiguous_query(field_name, type_hint, found.values())

    # No match => no change, search exactly what was requested
    return None


@attr.s
class PulpSearch(object):
    # Helper class representing a prepared Pulp search.
    # Usually just a filters dict, but may include type_ids
    # and fields for unit searches.
    filters = attr.ib(type=dict)
    type_ids = attr.ib(type=list, default=None)
    unit_fields = attr.ib(type=list, default=None)


class UnitTypeAccumulator(object):
    # A helper to accumulate info on the unit types we're dealing with
    # within a search:
    # - collects type_ids (the types we're searching for)
    # - collects unit_fields (the fields we want to query)
    # - complains if criteria is too complicated to gather a single consistent
    #   list of type_ids for the entire search
    #
    def __init__(self):
        self.can_accumulate = True
        self.type_ids = []

        # When no fields are requested, this must remain as None in order
        # to indicate that no field limits should be applied at all.
        self.unit_fields = None

    def accumulate_from_criteria(self, crit, match_expr):
        assert isinstance(crit, FieldMatchCriteria)

        # Accumulate type IDs here
        self.accumulate_from_match(match_expr)

        # And if this is specifically a criteria on unit type with
        # fields, accumulate those too
        if isinstance(crit, UnitTypeMatchCriteria) and crit._unit_fields is not None:
            self.unit_fields = self.unit_fields or set()
            self.unit_fields.update(crit._unit_fields)

    def accumulate_from_match(self, match_expr):
        # Are we still in a state where accumulation is possible?
        if not self.can_accumulate:
            raise ValueError(
                (
                    "Can't serialize criteria for Pulp query; too complicated. "
                    "Try simplifying the query with respect to unit_type/content_type_id."
                )
            )

        # OK, we can accumulate if it's a supported expression type.
        if isinstance(match_expr, dict) and list(match_expr.keys()) == ["$eq"]:
            self.type_ids = [match_expr["$eq"]]
        elif isinstance(match_expr, dict) and list(match_expr.keys()) == ["$in"]:
            self.type_ids = match_expr["$in"]
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


def search_for_criteria(
    criteria, type_hint=None, unit_type_accum=None, accum_only=None
):
    # convert a Criteria object to a PulpSearch with filters as used in the Pulp 2.x API:
    # https://docs.pulpproject.org/dev-guide/conventions/criteria.html#search-criteria
    #
    # type_hint optionally provides the class expected to be found by this search.
    # This can impact the application of certain criteria, e.g. it will affect
    # field mappings looked up by FieldMatchCriteria.

    if type_hint is Unit and accum_only is None:
        # If the caller asked for a generic Unit type hint, we'll do two passes.
        # The first pass tries to figure out exactly what kind of Unit subtype is
        # being searched for. This is important because the same field might exist
        # on different models but be stored in Pulp in different ways (e.g.
        # FileUnit.version vs ModulemdUnit.version).
        accum = UnitTypeAccumulator()
        search_for_criteria(criteria, type_hint, accum, accum_only=True)

        # We should now know what type_ids we want to query. Map them back to
        # a specific unit type.
        unit_classes = set()
        for type_id in accum.type_ids:
            unit_class = class_for_type_id(type_id)
            if unit_class:
                unit_classes.add(unit_class)

        # If the type IDs map to exactly one unit subtype, then we update our
        # type_hint to be more accurate and continue.
        # Otherwise any field ambiguities should be detected later on
        # and a helpful error raised telling the caller to be more specific
        # with their query.
        if len(unit_classes) == 1:
            type_hint = list(unit_classes)[0]

    if criteria is None or isinstance(criteria, TrueCriteria):
        return PulpSearch(filters={})

    unit_type_accum = unit_type_accum or UnitTypeAccumulator()

    if isinstance(criteria, AndCriteria):
        clauses = [
            search_for_criteria(
                c, type_hint, unit_type_accum, accum_only=accum_only
            ).filters
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
        with unit_type_accum.no_accumulate:
            filters = {
                "$or": [
                    search_for_criteria(
                        c, type_hint, unit_type_accum, accum_only=accum_only
                    ).filters
                    for c in criteria._operands
                ]
            }

    elif isinstance(criteria, FieldMatchCriteria):
        field = criteria._field
        matcher = criteria._matcher

        # Figure out the Pulp field being referenced here.
        #
        # If in accumulate-only mode (to calculate type_ids) we should skip this for now
        # because we may not have the final type_hint yet, which can lead to ambiguity.
        # content_type_id field itself is an exception as skipping that would interfere
        # with the calculation of type_ids.
        mapped = None
        if not accum_only or field == "content_type_id":
            mapped = map_field_for_type(field, matcher, type_hint)
        if mapped:
            field, matcher = mapped

        match_expr = field_match(matcher)

        # If we are looking at the special _content_type_id field
        # for the purpose of a unit search...
        if field == "_content_type_id" and issubclass(type_hint, Unit):
            # We should not include this into filters, but instead
            # attempt to accumulate it into type_ids_out.
            # This is because type_ids needs to be serialized into the
            # top-level 'criteria' and not 'filters', and there are
            # additional restrictions on its usage.
            unit_type_accum.accumulate_from_criteria(criteria, match_expr)

            filters = {}
        else:
            filters = {field: match_expr}

    else:
        raise TypeError("Not a criteria: %s" % repr(criteria))

    return PulpSearch(
        filters=filters,
        type_ids=unit_type_accum.type_ids[:],
        unit_fields=sorted(unit_type_accum.unit_fields)
        if unit_type_accum.unit_fields is not None
        else None,
    )


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
