import datetime

import attr
import sys
import pytest

import pubtools.pulplib

from .assertions import assert_model_invariants


# These are some classes which currently fail the model tests.
XFAIL_CLASSES = [
    pubtools.pulplib.Page,
    pubtools.pulplib.ContainerImageRepository,
    pubtools.pulplib.Distributor,
    pubtools.pulplib.FileRepository,
    pubtools.pulplib.FileUnit,
    pubtools.pulplib.MaintenanceEntry,
    pubtools.pulplib.MaintenanceReport,
    pubtools.pulplib.ModulemdUnit,
    pubtools.pulplib.PublishOptions,
    pubtools.pulplib.Repository,
    pubtools.pulplib.RpmUnit,
    pubtools.pulplib.Task,
    pubtools.pulplib.Unit,
    pubtools.pulplib.YumRepository,
]


def test_invariants(model_object):
    """Test that the given object satisfies all expected invariants of model objects."""

    # Checking for *exact* types is intentional here to limit scope of xfail:
    # pylint: disable=unidiomatic-typecheck

    try:
        assert_model_invariants(model_object)
    except:
        if type(model_object) in XFAIL_CLASSES:
            pytest.xfail("class is known to be buggy")
        raise

    # If it didn't fail, it must not be listed in XFAIL
    assert type(model_object) not in XFAIL_CLASSES


def public_model_objects():
    """Returns a default-constructed instance of every public model class
    found in pubtools.pulplib.
    """
    public_symbols = dir(pubtools.pulplib)
    public_symbols = [sym for sym in public_symbols if not sym.startswith("_")]

    public_classes = [getattr(pubtools.pulplib, sym) for sym in public_symbols]
    public_classes = [klass for klass in public_classes if attr.has(klass)]

    return [default_object(klass) for klass in public_classes]


def default_for_field(field):
    # Certain fields with known strict semantics
    value_by_name = {"sha256sum": "a" * 64, "sha1sum": "b" * 40, "md5sum": "c" * 32}

    # Generic defaults for certain types
    value_by_type = {
        str: "test",
        int: 123,
        datetime.datetime: datetime.datetime(2019, 9, 4, 12, 9, 30),
    }

    if sys.version_info.major == 2:
        value_by_type[basestring] = "test"

    if field.name in value_by_name:
        return value_by_name[field.name]
    if field.type in value_by_type:
        return value_by_type[field.type]

    # Try a default-constructed object.
    return field.type()


def all_fields(klass):
    """Returns all attr fields on klass and all base classes."""
    out = attr.fields(klass)
    for base in klass.__bases__:
        if attr.has(base):
            out = out + attr.fields(base)
    return out


def default_object(klass):
    """Return an instance of attrs-using klass, constructed with minimal arguments.
    This means:

    - any fields with a declared default will use that default
    - any other fields have basic defaults injected
    """
    args = {}

    for field in all_fields(klass):
        if field.default is not attr.NOTHING:
            # There's a default, then no arg needed
            continue
        if field.name.startswith("_"):
            # Internal field
            continue
        if field.name in args:
            # Already calculated field from a derived class,
            # no need to recalculate for base
            continue
        if not field.type:
            # No type declared, try None as default
            args[field.name] = None
        else:
            args[field.name] = default_for_field(field)

    return klass(**args)


@pytest.fixture(params=public_model_objects(), ids=lambda object: type(object).__name__)
def model_object(request):
    """This fixture yields an object for every public attrs-using class
    in the library."""
    yield request.param
