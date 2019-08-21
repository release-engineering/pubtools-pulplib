import pytest

from pubtools.pulplib import Criteria, Matcher, Repository

from pubtools.pulplib._impl.client.search import filters_for_criteria


def test_eng_product_in():
    """eng_product is mapped correctly"""
    crit = Criteria.with_field_in("eng_product_id", [12, 34, 56])
    assert filters_for_criteria(crit, Repository) == {
        "notes.eng_product": {"$in": ["12", "34", "56"]}
    }


def test_is_temporary():
    """is_temporary is mapped correctly"""
    crit = Criteria.with_field("is_temporary", True)
    assert filters_for_criteria(crit, Repository) == {
        "notes.pub_temp_repo": {"$eq": True}
    }


def test_type():
    """type is mapped correctly"""
    crit = Criteria.with_field("type", Matcher.regex("foobar"))
    assert filters_for_criteria(crit, Repository) == {
        "notes._repo-type": {"$regex": "foobar"}
    }


def test_signing_keys():
    """signing_keys are mapped correctly"""
    crit = Criteria.with_field("signing_keys", ["abc", "def", "123"])
    assert filters_for_criteria(crit, Repository) == {
        "notes.signatures": {"$eq": "abc,def,123"}
    }


def test_created():
    """created is mapped correctly"""
    # TODO: there is no datetime => string implicit conversion right now.
    #
    # Should we do that? Right now, it doesn't seem all that useful because
    # there's probably no usecase to search for an exact datetime anyway.
    #
    # In practice, searching by datetime probably is useful only with $lt
    # or $gt, which is not supported by this library at all, at the time
    # of writing.
    crit = Criteria.with_field("created", "20190814T15:16Z")
    assert filters_for_criteria(crit, Repository) == {
        "notes.created": {"$eq": "20190814T15:16Z"}
    }


def test_unsearchable():
    """passing a field which can't be mapped directly to Pulp raises an error"""
    crit = Criteria.with_field("relative_url", "foobar")
    with pytest.raises(NotImplementedError) as exc:
        filters_for_criteria(crit, Repository)
    assert "Searching on field relative_url is not supported" in str(exc.value)
