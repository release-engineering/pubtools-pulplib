import pytest

from pubtools.pulplib._impl.fake.rpmlib import _parse_dep_relation


@pytest.mark.parametrize(
    "flag, expected_relation",
    [
        (0x00, None),
        (0x02, "LT"),
        (0x04, "GT"),
        (0x08, "EQ"),
        (0x0A, "LE"),
        (0x0C, "GE"),
    ],
)
def test_parse_deps_relation(flag, expected_relation):
    """
    Tests expected value of relation according to input flags.
    """
    relation = _parse_dep_relation(flag)

    assert relation == expected_relation
