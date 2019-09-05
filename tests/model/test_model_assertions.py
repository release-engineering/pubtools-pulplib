# This file contains tests for the model-related assertions themselves
# to prove that the assertions aren't simply passing without verifying anything.
import attr
from attr import validators
import pytest

from .assertions import assert_model_invariants


def test_wrong_type():
    """An object with an attribute not matching defined 'type' should fail tests."""

    @attr.s(frozen=True)
    class BadType(object):
        id = attr.ib(type=str)

    instance = BadType(id=12345)

    with pytest.raises(AssertionError) as exc:
        assert_model_invariants(instance)

    assert "BadType.id should be a str but is not" in str(exc.value)


def test_unvalidated_type():
    """An object with an attribute with unvalidated type should fail"""

    @attr.s(frozen=True)
    class Unvalidated(object):
        my_attr = attr.ib(type=str)

    instance = Unvalidated(my_attr="foo")

    with pytest.raises(AssertionError) as exc:
        assert_model_invariants(instance)

    assert "copying with wrong type for my_attr was possible" in str(exc.value)


def test_bad_hash():
    """An object which is not hashable should fail tests."""

    @attr.s(frozen=True, hash=False)
    class BadHash(object):
        id = attr.ib(type=str, validator=validators.instance_of(str))

        def __hash__(self):
            raise TypeError("Can't hash")

    instance = BadHash(id="bad-hash")

    with pytest.raises(TypeError):
        assert_model_invariants(instance)


def test_bad_copied_hash():
    """An object whose copy has a different hash value will fail tests."""

    callnum = []

    @attr.s(frozen=True, hash=False)
    class BadHashOnCopy(object):
        id = attr.ib(type=str, validator=validators.instance_of(str), hash=True)

        def __hash__(self):
            callnum.append(None)
            return hash(tuple(callnum))

    instance = BadHashOnCopy(id="some-object")

    with pytest.raises(AssertionError) as exc:
        assert_model_invariants(instance)

    assert "hash differs" in str(exc.value)


def test_bad_copied_equality():
    """An object whose copy is not equal to the original will fail tests."""

    @attr.s(init=False, hash=False, frozen=True)
    class BadCopy(object):
        some_attr = attr.ib(
            default=None,
            type=str,
            validator=validators.optional(validators.instance_of(str)),
        )

        def __init__(self, some_attr):
            # Handle this argument oddly so that copying this class
            # doesn't actually get you a plain copy
            self.__dict__["some_attr"] = some_attr + "-suffix"

        def __hash__(self):
            # to make it get past the hash check
            return 0

    instance = BadCopy(some_attr="abc")

    with pytest.raises(AssertionError) as exc:
        assert_model_invariants(instance)

    assert "copied object is not equal" in str(exc.value)
