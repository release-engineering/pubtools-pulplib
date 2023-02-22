import pytest

from mock import Mock

from pubtools.pulplib._impl.compat_attr import validators

from pubtools.pulplib._impl.model.validate import NamedMappingValidator


def test_named_mapping_validator_extra_keys():
    validator = NamedMappingValidator(
        mapping={"foo": validators.instance_of(str)}, type_=dict
    )
    with pytest.raises(ValueError):
        validator(None, Mock(name="attr"), {"foo": "1", "bar": "2"})


def test_named_mapping_validator_missing_keys():
    validator = NamedMappingValidator(
        mapping={
            "foo": validators.instance_of(str),
            "bar": validators.instance_of(str),
        },
        type_=dict,
    )
    with pytest.raises(ValueError):
        validator(None, Mock(name="attr"), {"foo": "1"})
