from pubtools.pulplib import ErratumUnit

from pubtools.pulplib._impl.fake.units import is_erratum_version_newer


def test_is_erratum_version_newer():
    """Tests edge cases of internal helper is_erratum_version_newer which are
    cumbersome to verify using public API.
    """

    # Helper to get a unit with a particular version (we don't care about other fields)
    def u(version=None):
        return ErratumUnit(id="whatever", version=version)

    # Empty field on new unit means it's never considered newer (regardless
    # of value on the old unit)
    assert not is_erratum_version_newer(u(), u())
    assert not is_erratum_version_newer(u("0"), u())
    assert not is_erratum_version_newer(u("-3"), u())

    # Old field defaults to 0
    assert not is_erratum_version_newer(u(), u("-1"))
    assert not is_erratum_version_newer(u(), u("0"))
    assert is_erratum_version_newer(u(), u("0.1"))

    # Boring comparisons where everything works normally
    assert is_erratum_version_newer(u("10"), u("20"))
    assert not is_erratum_version_newer(u("20"), u("10"))

    # If *either* field is non-numeric, it's always treated as newer
    assert is_erratum_version_newer(u("oops not a number"), u("10"))
    assert is_erratum_version_newer(u("10"), u("oops not a number"))
    assert is_erratum_version_newer(u("2:30"), u("dentist time"))
