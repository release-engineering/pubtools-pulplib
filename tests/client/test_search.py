import pytest
import datetime

from pubtools.pulplib import Criteria, Matcher

from pubtools.pulplib._impl.client.search import (
    filters_for_criteria,
    field_match,
    validate_type_ids,
)


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


def test_field_regex_criteria():
    """with_field with regex is translated to a mongo fragment as expected."""

    assert filters_for_criteria(
        Criteria.with_field("some.field", Matcher.regex("abc"))
    ) == {"some.field": {"$regex": "abc"}}


def test_field_less_than_criteria():
    """with_field with less_than is translated as expected for
    date and non-date types
    """
    publish_date = datetime.datetime(2019, 8, 27, 0, 0, 0)
    c1 = Criteria.with_field("num_field", Matcher.less_than(5))
    c2 = Criteria.with_field("date_field", Matcher.less_than(publish_date))

    assert filters_for_criteria(c1) == {"num_field": {"$lt": 5}}
    assert filters_for_criteria(c2) == {
        "date_field": {"$lt": {"$date": "2019-08-27T00:00:00Z"}}
    }


def test_non_matcher():
    """field_match raises if invoked with something other than a matcher.

    This is not possible to reach by public API alone; it'd be an internal bug
    if this exception is ever raised.
    """

    with pytest.raises(TypeError) as exc_info:
        field_match("oops not a matcher")

    assert "Not a matcher" in str(exc_info.value)


def test_dict_matcher_value():
    """criteria using a dict as matcher value"""

    crit = Criteria.with_field(
        "created",
        Matcher.less_than({"created_date": datetime.datetime(2019, 9, 4, 0, 0, 0)}),
    )

    assert filters_for_criteria(crit) == {
        "created": {"$lt": {"created_date": {"$date": "2019-09-04T00:00:00Z"}}}
    }


def test_valid_type_ids(caplog):
    assert validate_type_ids(["srpm", "iso", "quark", "rpm"]) == ["srpm", "iso", "rpm"]
    for m in ["Invalid content type ID(s):", "quark"]:
        assert m in caplog.text


def test_invalid_type_ids():
    """validate_type_ids raises if called without valid criteria"""
    with pytest.raises(ValueError) as e:
        validate_type_ids("quark")

    assert "Must provide valid content type ID(s):" in str(e)
    assert "iso, rpm, srpm, modulemd, modulemd_defaults" in str(e)


def test_invalid_type_ids_type():
    """validate_type_ids raises if called without valid criteria"""
    with pytest.raises(TypeError) as e:
        validate_type_ids({"srpm": "some-srpm"})

    assert "Expected str, list, or tuple, got %s" % type({}) in str(e)
