from pubtools.pulplib._impl.criteria import (
    Criteria,
    AndCriteria,
    OrCriteria,
    FieldEqCriteria,
    FieldInCriteria,
    TrueCriteria,
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

    if isinstance(criteria, FieldEqCriteria):
        field = criteria._field
        value = criteria._value

        if value is Criteria.exists:
            return {field: {"$exists": True}}

        return {field: {"$eq": value}}

    if isinstance(criteria, FieldInCriteria):
        field = criteria._field
        value = criteria._value

        return {field: {"$in": value}}

    raise TypeError("Not a criteria: %s" % repr(criteria))
