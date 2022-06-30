import pytest
import textwrap

from pubtools.pulplib import Criteria, Unit, FileUnit

from pubtools.pulplib._impl.client.search import (
    filters_for_criteria,
    field_match,
)


def test_error_on_ambiguous_field():
    """A query with an ambiguous field reference can't be executed."""
    crit = Criteria.with_field("version", "abc123")
    message = textwrap.dedent(
        """
        Field 'version' is ambiguous.
        A subtype of Unit must be provided to select one of the following groups:
          ErratumUnit.version, ModulemdUnit.version, RpmUnit.version
          FileUnit.version
    """
    ).strip()

    # It should raise
    with pytest.raises(Exception) as excinfo:
        filters_for_criteria(crit, type_hint=Unit)

    # It should tell us what the problem was
    assert message in str(excinfo.value)


def test_ambiguous_field_resolution():
    """A field definition which would be ambiguous on Unit is disambiguated by giving
    a specific Unit subclass in the criteria.
    """

    crit = Criteria.and_(
        Criteria.with_unit_type(FileUnit), Criteria.with_field("version", "abc123")
    )

    # It should run OK and use the correct FileUnit storage for version field
    assert filters_for_criteria(crit, type_hint=Unit) == {
        "pulp_user_metadata.version": {"$eq": "abc123"}
    }
