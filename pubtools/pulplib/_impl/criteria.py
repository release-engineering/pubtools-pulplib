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

from frozenlist2 import frozenlist

from pubtools.pulplib._impl import compat_attr as attr

from .model.unit import type_ids_for_class
from .model.attr import PULP2_FIELD


FieldNamePair = collections.namedtuple(
    "FieldNamePair", ["model_field_name", "pulp_field_name"]
)


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
    def with_unit_type(cls, unit_type, **kwargs):
        """Args:
            unit_type (class)
                A subclass of :class:`~pubtools.pulplib.Unit`.

            unit_fields (Iterable[str])
                Names of the desired field(s) to include in response to a search
                using this criteria. If omitted, all fields are included.

                Some fields will always be included even when not requested.

        Returns:
            Criteria
                criteria for finding units of type ``unit_type`` populated with
                (at least) the fields from ``unit_fields``.

        .. versionadded:: 2.14.0

        .. versionadded:: 2.33.0
            Introduced ``unit_fields``.
        """

        # This is mainly a thin wrapper for searching on content_type_id which allows
        # the caller to avoid having to handle the (unit class <=> type id) mapping.
        type_ids = type_ids_for_class(unit_type)
        if not type_ids:
            raise TypeError("Expected a Unit type, got: %s" % repr(unit_type))

        unit_fields = kwargs.pop("unit_fields", None)
        if unit_fields is not None:
            # We have some non-default set of fields to query.
            # We must do the following:
            # - ensure that we also include all the mandatory fields for this model
            # - generate pairs of (model field, pulp field) names, as we'll need both

            model_field_names = set(unit_fields)

            model_fields_dict = attr.fields_dict(unit_type)
            for field in model_fields_dict.values():
                if field.default is attr.NOTHING:
                    # No default => it's mandatory to use this field
                    model_field_names.add(field.name)

            # Now build up (model, pulp) pairs
            pairs = set()
            for model_field_name in model_field_names:
                # The default/fallback is to assume that the pulp field is named the
                # same as the model field...
                pulp_field_name = model_field_name

                # ... but if the field exists and declares an explicit PULP2_FIELD then we
                # use that instead
                field = model_fields_dict.get(model_field_name)
                if field and field.metadata.get(PULP2_FIELD):
                    # We have a defined pulp field, so use it.
                    # Note we only care about the first component of the field, because that's
                    # all the granularity supported by Pulp search API (e.g. if actual field
                    # is pulp_user_metadata.description, we need to query pulp_user_metadata).
                    pulp_field_name = field.metadata[PULP2_FIELD].split(".")[0]

                pairs.add(FieldNamePair(model_field_name, pulp_field_name))

            unit_fields = tuple(sorted(pairs))

        return UnitTypeMatchCriteria(
            "content_type_id", Matcher.in_(type_ids), unit_fields
        )

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


@attr.s(frozen=True)
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

    def __str__(self):
        return "=~/%s/" % self._pattern


@attr.s(frozen=True)
class EqMatcher(Matcher):
    _value = attr.ib()

    def _map(self, fn):
        return attr.evolve(self, value=fn(self._value))

    def __str__(self):
        return "==%s" % repr(self._value)


def iterable_nonstr_then_frozenlist(values):
    if isinstance(values, Iterable) and not isinstance(values, six.string_types):
        return frozenlist(values)
    raise ValueError("Must be an iterable: %s" % repr(values))


@attr.s(frozen=True)
class InMatcher(Matcher):
    _values = attr.ib(converter=iterable_nonstr_then_frozenlist)

    def _map(self, fn):
        return attr.evolve(self, values=[fn(x) for x in self._values])

    def __str__(self):
        return " IN %s" % repr(self._values)


@attr.s(frozen=True)
class ExistsMatcher(Matcher):
    def __str__(self):
        return " EXISTS"


@attr.s(frozen=True)
class LessThanMatcher(Matcher):
    _value = attr.ib()

    def _map(self, fn):
        return attr.evolve(self, value=fn(self._value))

    def __str__(self):
        return "<%s" % repr(self._value)


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


@attr.s(frozen=True)
class FieldMatchCriteria(Criteria):
    _field = attr.ib()
    _matcher = attr.ib(converter=coerce_to_matcher)

    def __str__(self):
        matcher = str(self._matcher)
        out = "%s%s" % (self._field, matcher)

        if " " in matcher:
            out = "(%s)" % out
        return out


@attr.s(frozen=True)
class UnitTypeMatchCriteria(FieldMatchCriteria):
    # This specialization of FieldMatchCriteria is used to match on unit types
    # while also keeping info on the fields of interest to the user.
    _unit_fields = attr.ib()


@attr.s(frozen=True)
class AndCriteria(Criteria):
    _operands = attr.ib()

    def __str__(self):
        if not self._operands:
            return "<empty AND>"

        if len(self._operands) == 1:
            return str(self._operands[0])

        return "(" + " AND ".join([str(o) for o in self._operands]) + ")"


@attr.s(frozen=True)
class OrCriteria(Criteria):
    _operands = attr.ib()

    def __str__(self):
        if not self._operands:
            return "<empty OR>"

        if len(self._operands) == 1:
            return str(self._operands[0])

        return "(" + " OR ".join([str(o) for o in self._operands]) + ")"


class TrueCriteria(Criteria):
    def __str__(self):
        return "TRUE"
