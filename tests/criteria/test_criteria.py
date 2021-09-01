import pytest

from pubtools.pulplib import Criteria


def test_field_in_str_invalid():
    """Criteria.with_field_in raises if provided field value is a string.

    This is checked specifically because strings are iterable, so it could
    seem to work, but it's almost certainly an error if the caller provided
    a string.
    """
    with pytest.raises(ValueError) as exc_info:
        Criteria.with_field_in("x", "someval")
    assert "Must be an iterable: 'someval'" in str(exc_info.value)


def test_unit_type_invalid():
    """Criteria.with_unit_type raises if provided value isn't a unit subclass."""
    with pytest.raises(TypeError) as exc_info:
        Criteria.with_unit_type([1, 2, 3])
    assert "Expected a Unit type, got: [1, 2, 3]" in str(exc_info.value)
