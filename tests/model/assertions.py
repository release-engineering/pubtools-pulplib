import pytest
import attr


def assert_model_invariants(model_object):
    """Verify that a model object (an attrs-using class) satisfies certain invariants
    which should always be true of any model object.  These include at least:

    - attrs of a defined "type" are genuinely instances of that type (or None)
    - object is hashable
    - object can be copied
    - object is equal to its copy
    - object's hash is equal to hash of its copy

    This suite of assertions is meant to protect against certain mistakes which
    can easily be made when defining an attrs-based class.
    """
    if model_object is None:
        # Test trivially passes
        return

    assert_model_fields(model_object)

    copy = attr.evolve(model_object)
    assert hash(model_object) == hash(copy), "hash differs on copied object"
    assert model_object == copy, "copied object is not equal"


def assert_model_fields(model_object):
    """Assert every defined field on a model object meets certain invariants:

    - actual value matches declared type (or None)
    - not possible to create a copy using wrong type for the field
    """
    klass = type(model_object)
    fields = attr.fields(klass)

    # Only those with a defined type are testable
    fields = [f for f in fields if f.type]

    for field in fields:
        # Every field must have a type defined
        assert field.type, "%s.%s is missing a type" % (klass.__name__, field.name)

        value = getattr(model_object, field.name)
        if value is not None:
            # These tests only valid on non-None value.

            assert isinstance(
                value, field.type
            ), "%s.%s should be a %s but is not: %s" % (
                klass.__name__,
                field.name,
                field.type.__name__,
                model_object,
            )

            if field.type is list:
                # Any lists on our model objects should be immutable.
                assert_list_immutable(value)

            # If this object is also an attrs-using class,
            # test it deeply
            if attr.has(type(value)):
                assert_model_invariants(value)

        # It should not be possible to create a copy of this object
        # with a field of an incorrect type.
        assert_type_validated(model_object, field)

        # It should not be possible to directly mutate this object.
        with pytest.raises(attr.exceptions.FrozenInstanceError):
            setattr(model_object, field.name, value)


def assert_type_validated(model_object, field):
    """Verify that model_object doesn't accept values of wrong type in field.

    This test can find some (but not all) cases where a model fails to validate
    that input data is of the expected type.
    """

    copy = None
    copy_args = {field.name: object()}

    # The way this test is written, it only works if the type is not
    # declared as `object`.  It doesn't seem like there would ever
    # be a reason to do that, but let's make sure we fail early if
    # that does happen
    assert field.type is not object, "test cannot handle type=object!"

    try:
        copy = attr.evolve(model_object, **copy_args)
    except Exception:  # pylint: disable=broad-except
        # exception is expected (we don't really care what type of exception,
        # it's unreasonably cumbersome to force e.g. TypeError everywhere)
        return

    assert copy is None, "copying with wrong type for %s was possible! copy=%s" % (
        field.name,
        copy,
    )


def assert_list_immutable(value):
    """Verifies that a given list is immutable (all operations which would normally
    write to the list instead raise).
    """

    with pytest.raises(NotImplementedError):
        value[0] = None

    with pytest.raises(NotImplementedError):
        del value[0]

    with pytest.raises(NotImplementedError):
        value += None

    with pytest.raises(NotImplementedError):
        value.insert(0, None)

    with pytest.raises(NotImplementedError):
        value.append(None)

    with pytest.raises(NotImplementedError):
        value.extend([None])

    with pytest.raises(NotImplementedError):
        value.pop()

    with pytest.raises(NotImplementedError):
        value.remove(None)
