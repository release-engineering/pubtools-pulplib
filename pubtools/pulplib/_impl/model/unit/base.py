import re

from ..common import PulpObject
from ..attr import pulp_attrib, PULP2_FIELD
from ...util import dict_put
from ... import compat_attr as attr
from ...schema import load_schema


UNIT_CLASSES = {}


def unit_type(pulp_type):
    # decorator for Unit subclasses, registers against a
    # particular value of type_id.
    def decorate(klass):
        UNIT_CLASSES[pulp_type] = klass
        return klass

    return decorate


def type_ids_for_class(unit_class):
    # Given a concrete Unit subclass, returns those Pulp type id(s)
    # which may be used to find/load an object of that class.
    out = []

    for pulp_type, klass in UNIT_CLASSES.items():
        if klass is unit_class:
            out.append(pulp_type)

    return sorted(out)


@attr.s(kw_only=True, frozen=True)
class Unit(PulpObject):
    """Represents a Pulp unit (a single piece of content).

    .. versionadded:: 1.5.0
    """

    _SCHEMA = load_schema("unit")

    content_type_id = pulp_attrib(type=str, pulp_field="_content_type_id")
    """The type of this unit.

    This value will match one of the content types returned by
    :meth:`~pubtools.pulplib.Client.get_content_type_ids`.
    """

    @classmethod
    def from_data(cls, data):
        # delegate to concrete subclass as needed
        if cls is Unit:
            type_id = data.get("_content_type_id")
            for klass_type_id, klass in UNIT_CLASSES.items():
                if klass_type_id == type_id:
                    return klass.from_data(data)

        return super(Unit, cls).from_data(data)

    @classmethod
    def _from_task_data(cls, data):
        # Like from_data, but massages the data from the format used in
        # task units_successful, which is slightly different from content search.
        unit_data = {}

        unit_data["_content_type_id"] = data.get("type_id")
        unit_data.update(data.get("unit_key") or {})

        return cls.from_data(unit_data)

    # A validator shared by various subclasses
    def _check_sum(self, value, sumtype, length):
        if value is None:
            return
        if not re.match(r"^[a-f0-9]{%s}$" % length, value):
            raise ValueError("Not a valid %s: %s" % (sumtype, value))

    @property
    def _usermeta(self):
        # Returns pulp_user_metadata dict for this unit.
        out = {}

        for field in self._usermeta_fields():
            pulp_field = field.metadata.get(PULP2_FIELD)
            python_value = getattr(self, field.name)
            pulp_value = PulpObject._any_to_data(python_value)
            dict_put(out, pulp_field, pulp_value)

        return out.get("pulp_user_metadata") or {}

    @classmethod
    def _usermeta_fields(cls):
        # Returns the subset of fields on this class which are stored under the
        # pulp_user_metadata dict. In public API we refer to these as 'mutable' fields.
        return [
            fld
            for fld in attr.fields(cls)
            if fld.metadata.get(PULP2_FIELD).startswith("pulp_user_metadata.")
        ]

    @classmethod
    def _usermeta_from_kwargs(cls, **kwargs):
        # Given kwargs mapping to mutable fields on this unit class, returns a dict
        # of the form:
        #
        #   {"pulp_user_metadata": {...serialized mutable fields}}
        #
        # ...suitable for merging into a 'metadata' dict on a content upload.
        #
        # If any of the kwargs do not map to a mutable field, an exception is raised.
        #
        fields = cls._usermeta_fields()
        out = {}

        for field in fields:
            if not field.name in kwargs:
                continue

            pulp_field = field.metadata.get(PULP2_FIELD)
            python_value = kwargs.pop(field.name)
            pulp_value = PulpObject._any_to_data(python_value)
            dict_put(out, pulp_field, pulp_value)

        # Ensure that we have consumed all arguments; if not, that means the
        # caller tried to set something we don't support.
        remaining = sorted(kwargs.keys())
        if remaining:
            raise ValueError(
                "Not mutable %s field(s): %s" % (cls.__name__, ", ".join(remaining))
            )

        return out


def schemaless_init(cls, data):
    # Construct and return an instance of (attrs-using) cls from
    # pulp data, where data in pulp has no schema at all (and hence
    # every field could possibly be missing).
    kwargs = {}
    for key in [fld.name for fld in attr.fields(cls)]:
        if key in data:
            kwargs[key] = data[key]

    return cls(**kwargs)
