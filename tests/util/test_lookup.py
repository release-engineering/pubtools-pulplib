import pytest

from pubtools.pulplib._impl.util import lookup


def test_lookup_nested_found():
    """lookup can find elements in nested dicts"""
    data = {"a": {"b": {"c": 123}}}

    assert lookup(data, "a.b.c") == 123


def test_lookup_nested_absent_raise():
    """lookup raises KeyError for absent items by default"""
    data = {"a": {"b": {"c": 123}}}

    with pytest.raises(KeyError) as error:
        lookup(data, "a.b.d")

    assert "a.b.d" in str(error)


def test_lookup_nested_absent_default():
    """lookup returns given default value for failed lookup"""
    data = {"a": {"b": {"c": 123}}}

    assert lookup(data, "a.d.c", "my-default") == "my-default"
