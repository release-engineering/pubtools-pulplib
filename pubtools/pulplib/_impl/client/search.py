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


def filters_for_criteria(criteria):
    # convert a Criteria object to a filters dict as used in the Pulp 2.x API:
    # https://docs.pulpproject.org/dev-guide/conventions/criteria.html#search-criteria
    if criteria is None or isinstance(criteria, TrueCriteria):
        return {}

    if isinstance(criteria, AndCriteria):
        return {"$and": [filters_for_criteria(c) for c in criteria._operands]}

    if isinstance(criteria, OrCriteria):
        return {"$or": [filters_for_criteria(c) for c in criteria._operands]}

    if isinstance(criteria, FieldMatchCriteria):
        field = criteria._field
        matcher = criteria._matcher

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
