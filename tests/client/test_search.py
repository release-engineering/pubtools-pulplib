from pubtools.pulplib import Criteria

from pubtools.pulplib._impl.client.search import filters_for_criteria


def test_null_criteria():
    """Searching for None or True translates to empty filters."""
    assert filters_for_criteria(None) == {}
    assert filters_for_criteria(Criteria.true()) == {}


def test_field_eq_criteria():
    """with_field is translated to a mongo fragment as expected."""
    assert filters_for_criteria(Criteria.with_field("some.field", "someval")) == {
        "some.field": {"$eq": "someval"}
    }


def test_field_exists_criteria():
    """with_field using 'exists' is translated to a mongo fragment as expected."""
    assert filters_for_criteria(Criteria.with_field("some.field", Criteria.exists)) == {
        "some.field": {"$exists": True}
    }


def test_field_in_criteria():
    """with_field_in is translated to a mongo fragment as expected."""
    assert filters_for_criteria(
        Criteria.with_field_in("some.field", ["val1", "val2"])
    ) == {"some.field": {"$in": ["val1", "val2"]}}


def test_field_and_criteria():
    """and is translated to a mongo fragment as expected."""
    c1 = Criteria.with_field("f1", "v1")
    c2 = Criteria.with_field("f2", "v2")
    assert filters_for_criteria(Criteria.and_(c1, c2)) == {
        "$and": [{"f1": {"$eq": "v1"}}, {"f2": {"$eq": "v2"}}]
    }


def test_field_or_criteria():
    """or is translated to a mongo fragment as expected."""
    c1 = Criteria.with_field("f1", "v1")
    c2 = Criteria.with_field("f2", "v2")
    assert filters_for_criteria(Criteria.or_(c1, c2)) == {
        "$or": [{"f1": {"$eq": "v1"}}, {"f2": {"$eq": "v2"}}]
    }
