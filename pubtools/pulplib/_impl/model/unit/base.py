import re

from ..common import PulpObject
from ..attr import pulp_attrib
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
