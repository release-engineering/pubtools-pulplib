import collections
import re
import warnings

import six

# Due to below block:
# pylint: disable=wrong-import-position

try:
    # python 3
    Iterable = collections.abc.Iterable  # pylint: disable=invalid-name
except AttributeError:  # pragma: no cover
    # python 2
    Iterable = collections.Iterable  # pylint: disable=invalid-name

from pubtools.pulplib._impl import compat_attr as attr

from .model.unit import type_ids_for_class


class Criteria(object):
    """Represents a Pulp search criteria.

    This is an opaque class which is not intended to be created
    or used directly. Instances of this class should be obtained and
    composed by calls to the documented class methods.

    Example - searching a repository:
        .. code-block:: python

            # With Pulp 2.x / mongo, this is roughly equivalent
            # to search fragment:
            #
            #  {"notes.my-field": {"$exists": True},
            #   "notes.other-field": {"$eq": ["a", "b", "c"]}}
            #
            crit = Criteria.and_(
                Criteria.with_field('notes.my-field', Matcher.exists()),
                Criteria.with_field('notes.other-field', ["a", "b", "c"])
            )

            # criteria may now be used with client to execute a search
            repos = client.search_repository(crit)

    Example - searching across all repos for a specific content type:
        .. code-block:: python

            crit = Criteria.and_(
                Criteria.with_unit_type(RpmUnit),
                Criteria.with_field("sha256sum", Matcher.in_([
                    "49ae93732fcf8d63fe1cce759664982dbd5b23161f007dba8561862adc96d063",
                    "6b30e91df993d96df0bef0f9d232d1068fa2f7055f13650208d77b43cd7c99f6"])))

            # Will find RpmUnit instances with above sums
            units = client.search_content(crit)
    """

    exists = object()
    # exists is undocumented and deprecated, use Matcher.exists() instead

    @classmethod
    def with_id(cls, ids):
        """Args:
            ids (str, list[str])
                An id or list of ids

        Returns:
            Criteria
                criteria for finding objects matching the given ID(s)
        """
        if isinstance(ids, six.string_types):
            return cls.with_field("id", ids)
        return cls.with_field("id", Matcher.in_(ids))

    @classmethod
    def with_field(cls, field_name, field_value):
        """Args:
            field_name (str)
                The name of a field.

                Supported field names include both model fields
                and Pulp fields.  See :ref:`model_fields` for information
                about these two types of fields.

                When Pulp fields are used, field names may contain a "." to
                indicate nesting, such as ``notes.created``.

            field_value
                :class:`Matcher`
                    A matcher to be applied against the field.

                object
                    Any value, to be matched against the field via
                    :meth:`Matcher.equals`.

        Returns:
            Criteria
                criteria for finding objects where ``field_name`` is present and
                matches ``field_value``.
        """
        return FieldMatchCriteria(field_name, field_value)

    @classmethod
    def with_unit_type(cls, unit_type):
        """Args:
            unit_type (class)
                A subclass of :class:`~pubtools.pulplib.Unit`.

        Returns:
            Criteria
                criteria for finding units of type ``unit_type``.

        .. versionadded:: 2.14.0
        """

        # This is just a thin wrapper for searching on content_type_id which allows
        # the caller to avoid having to handle the (unit class <=> type id) mapping.
        type_ids = type_ids_for_class(unit_type)
        if not type_ids:
            raise TypeError("Expected a Unit type, got: %s" % repr(unit_type))

        return FieldMatchCriteria("content_type_id", Matcher.in_(type_ids))

    @classmethod
    def with_field_in(cls, field_name, field_value):
        warnings.warn(
            "with_field_in is deprecated, use Matcher.in_() instead", DeprecationWarning
        )

        return cls.with_field(field_name, Matcher.in_(field_value))

    @classmethod
    def and_(cls, *criteria):
        """Args:
            criteria (list[Criteria])
                Any number of criteria.

        Returns:
            :class:`Criteria`
                criteria for finding objects which satisfy all of the input ``criteria``.
        """
        return AndCriteria(criteria)

    @classmethod
    def or_(cls, *criteria):
        """Args:
            criteria (list[Criteria])
                Any number of criteria.

        Returns:
            Criteria
                criteria for finding objects which satisfy any of the input ``criteria``.
        """
        return OrCriteria(criteria)

    @classmethod
    def true(cls):
        """
        Returns:
            Criteria
                a criteria which always matches any object.
        """
        return TrueCriteria()


class Matcher(object):
    """Methods for matching fields within a Pulp search query.

    Instances of this class are created by the documented class methods,
    and should be used in conjunction with :class:`Criteria` methods, such
    as :meth:`Criteria.with_field`.

    .. versionadded:: 1.1.0
    """

    @classmethod
    def equals(cls, value):
        """
        Matcher for a field which must equal exactly the given value.

        Arguments:
            value (object)
                An object to match against a field.
        """
        return EqMatcher(value)

    @classmethod
    def regex(cls, pattern):
        """
        Matcher for a field which must be a string and must match the given
        regular expression.

        Arguments:
            pattern (str)
                A regular expression to match against the field.
                The expression is not implicitly anchored.

                .. warning::

                    It is not defined which specific regular expression syntax is
                    supported. For portable code, callers are recommended to use
                    only the common subset of PCRE-compatible and Python-compatible
                    regular expressions.

        Raises:
            :class:`re.error`
                If the given pattern is not a valid regular expression.

        Example:

            .. code-block:: python

                # Would match any Repository where notes.my-field starts
                # with "abc"
                crit = Criteria.with_field('notes.my-field', Matcher.regex("^abc"))
        """

        return RegexMatcher(pattern)

    @classmethod
    def exists(cls):
        """
        Matcher for a field which must exist, with no specific value.

        Example:

            .. code-block:: python

                # Would match any Repository where notes.my-field exists
                crit = Criteria.with_field('notes.my-field', Matcher.exists())
        """
        return ExistsMatcher()

    @classmethod
    def in_(cls, values):
        """
        Returns a matcher for a field whose value equals one of the specified
        input values.

        Arguments:
            values (iterable)
                An iterable of values used to match a field.

        Example:

            .. code-block:: python

                # Would match any Repository where notes.my-field is "a", "b" or "c"
                crit = Criteria.with_field(
                    'notes.my-field',
                    Matcher.in_(["a", "b", "c"])
                )
        """
        return InMatcher(values)

    @classmethod
    def less_than(cls, value):
        """
        Returns a matcher for a field whose value is less than the specified input
        value.

        Arguments:
            value (object)
                An object to match against the field

        Example:
            .. code-block:: python

                # would match where last_publish is before "2019-08-27T00:00:00Z"
                # date comparison requires a datetime.datetime object
                crit = Criteria.with_field(
                    'last_publish',
                    Matcher.less_than(datetime.datetime(2019, 8, 27, 0, 0, 0))
                )

        .. versionadded:: 2.1.0
        """
        return LessThanMatcher(value)

    def _map(self, _fn):
        # Internal-only: return self with matched value mapped through
        # the given function. Intended to be overridden in subclasses
        # to support field conversions between Pulp and Python.
        return self


@attr.s
class RegexMatcher(Matcher):
    _pattern = attr.ib()

    @_pattern.validator
    def _check_pattern(self, _, pattern):
        # It must be a string.
        # Need an explicit check here because re.compile also succeeds
        # on already-compiled regex objects.
        if not isinstance(pattern, six.string_types):
            raise TypeError("Regex matcher expected string, got: %s" % repr(pattern))

        # Verify that the given value can really be compiled as a regex.
        re.compile(pattern)

    # Note: regex matcher does not implement _map since regex is defined only
    # in terms of strings, there are no meaningful conversions.


@attr.s
class EqMatcher(Matcher):
    _value = attr.ib()

    def _map(self, fn):
        return attr.evolve(self, value=fn(self._value))


@attr.s
class InMatcher(Matcher):
    _values = attr.ib()

    @_values.validator
    def _check_values(self, _, values):
        if isinstance(values, Iterable) and not isinstance(values, six.string_types):
            return
        raise ValueError("Must be an iterable: %s" % repr(values))

    def _map(self, fn):
        return attr.evolve(self, values=[fn(x) for x in self._values])


@attr.s
class ExistsMatcher(Matcher):
    pass


@attr.s
class LessThanMatcher(Matcher):
    _value = attr.ib()

    def _map(self, fn):
        return attr.evolve(self, value=fn(self._value))


def coerce_to_matcher(value):
    if isinstance(value, Matcher):
        return value

    if value is Criteria.exists:
        warnings.warn(
            "Criteria.exists is deprecated, use Matcher.exists() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return ExistsMatcher()

    return EqMatcher(value)


@attr.s
class FieldMatchCriteria(Criteria):
    _field = attr.ib()
    _matcher = attr.ib(converter=coerce_to_matcher)


@attr.s
class AndCriteria(Criteria):
    _operands = attr.ib()


@attr.s
class OrCriteria(Criteria):
    _operands = attr.ib()


class TrueCriteria(Criteria):
    pass
