import pytest

from pubtools.pulplib._impl.util import lookup


def test_lookup_nested_found():
    data = {"a": {"b": {"c": 123}}}

    assert lookup(data, "a.b.c") == 123


def test_lookup_nested_absent_raise():
    data = {"a": {"b": {"c": 123}}}

    with pytest.raises(KeyError) as error:
        lookup(data, "a.b.d")

    assert "a.b.d" in str(error)


def test_lookup_nested_absent_default():
    data = {"a": {"b": {"c": 123}}}

    assert lookup(data, "a.d.c", "my-default") == "my-default"
