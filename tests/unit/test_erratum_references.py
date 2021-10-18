from attr import evolve

import pytest

from pubtools.pulplib import ErratumUnit, ErratumReference


def test_erratum_validates_references():
    """It is not possible to pass incorrect types into an erratum reference list."""

    # Validation of references within the list is tested explicitly because deep
    # validation is uncommon across the model. We don't explicitly test it for every
    # field though.

    unit = ErratumUnit(id="RHBA-1234:56")
    ref = ErratumReference(href="https://example.com")

    # It starts out with absent references.
    assert unit.references is None

    # We can add an empty list OK...
    assert evolve(unit, references=[]).references == []

    # We can add a list with references OK...
    assert evolve(unit, references=[ref]).references == [ref]

    # But we cannot add a list with other stuff
    with pytest.raises(TypeError):
        evolve(unit, references=[ref, {"href": "abc123"}])
