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


class Criteria(object):
    """Represents a Pulp search criteria.

    This is an opaque class which is not intended to be created
    or used directly. Instances of this class should be obtained and
    composed by calls to the documented class methods.

    Example:
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
        return cls.with_field_in("id", ids)

    @classmethod
    def with_field(cls, field_name, field_value):
        """Args:
            field_name (str)
                The name of a field.

                Field names may contain a "." to indicate nested fields,
                such as ``notes.created``.

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


@attr.s
class RegexMatcher(Matcher):
    _pattern = attr.ib()

    @_pattern.validator
    def _check_pattern(self, _, pattern):
        re.compile(pattern)


@attr.s
class EqMatcher(Matcher):
    _value = attr.ib()


@attr.s
class InMatcher(Matcher):
    _values = attr.ib()

    @_values.validator
    def _check_values(self, _, values):
        if isinstance(values, Iterable) and not isinstance(values, six.string_types):
            return
        raise ValueError("Must be an iterable: %s" % repr(values))


@attr.s
class ExistsMatcher(Matcher):
    pass


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
