import pytest

from pubtools.pulplib import (
    ModulemdUnit,
    ModulemdDefaultsUnit,
)
from frozendict.core import frozendict  # pylint: disable=no-name-in-module
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


def test_convert_profile_value():
    """Profile and the values it contains should be immutable"""

    default_unit, md_unit = get_test_values()

    assert isinstance(default_unit.profiles, frozendict)
    assert isinstance(default_unit.profiles["1.0"], frozenlist)
    assert isinstance(md_unit.profiles, frozendict)
    assert isinstance(md_unit.profiles["default"], frozendict)
    assert isinstance(md_unit.profiles["default"]["rpms"], frozenlist)


def test_profiles_have_hash():
    """If two objects are equal, then they must have the same hashcode"""
    default_unit_1, md_unit_1 = get_test_values()
    default_unit_2, md_unit_2 = get_test_values()

    assert hash(default_unit_1) == hash(default_unit_2)
    assert hash(md_unit_1) == hash(md_unit_2)


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
