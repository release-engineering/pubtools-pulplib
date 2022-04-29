import sys
import pytest

from pubtools.pulplib import (
    ModulemdUnit,
    ModulemdDefaultsUnit,
)
from pubtools.pulplib._impl.compat_frozendict import frozendict
from frozenlist2 import frozenlist


def get_test_values():

    default_unit = ModulemdDefaultsUnit(
        unit_id="md_unit_id",
        name="md_unit_name",
        repo_id="md_unit_repo",
        profiles={"1.0": ["default"]},
    )

    md_unit = ModulemdUnit(
        unit_id="unit_id",
        name="name",
        stream="1.0",
        version=1,
        context="context",
        arch="x86_64",
        profiles={
            "default": {
                "description": "Default description",
                "rpms": ["rpm"],
            },
        },
    )
    return default_unit, md_unit


@pytest.mark.xfail(
    sys.version_info < (3, 0),
    reason="The conversion function checks if the value is already a frozendict, which is just "
    "dict in python2, so profiles and the contents wont be converted",
)
def test_convert_profile_value():
    """Profile and the values it contains should be immutable"""

    default_unit, md_unit = get_test_values()

    assert isinstance(default_unit.profiles, frozendict)
    assert isinstance(default_unit.profiles["1.0"], frozenlist)
    assert isinstance(md_unit.profiles, frozendict)
    assert isinstance(md_unit.profiles["default"], frozendict)
    assert isinstance(md_unit.profiles["default"]["rpms"], frozenlist)


@pytest.mark.xfail(
    sys.version_info < (3, 0),
    reason="Frozendict falls back to the default dict for Python2, so wont have a hash",
)
def test_profiles_have_hash():
    """If two objects are equal, then they must have the same hashcode"""
    default_unit_1, md_unit_1 = get_test_values()
    default_unit_2, md_unit_2 = get_test_values()

    assert hash(default_unit_1) == hash(default_unit_2)
    assert hash(md_unit_1) == hash(md_unit_2)


@pytest.mark.xfail(
    sys.version_info < (3, 0),
    reason="Frozendict falls back to the default dict for Python2, so wont throw exceptions",
)
def test_fail_on_modify_profiles():
    """Should fail when the profile attribute is modified"""
    default_unit, md_unit = get_test_values()
    with pytest.raises(AttributeError):
        default_unit.profiles.clear()

    with pytest.raises(TypeError):
        default_unit.profiles["1.0"] = ["modify"]

    with pytest.raises(NotImplementedError):
        default_unit.profiles["1.0"].append("modify")

    with pytest.raises(TypeError):
        md_unit.profiles["default"] = {}

    with pytest.raises(TypeError):
        md_unit.profiles["default"]["description"] = "modify"
