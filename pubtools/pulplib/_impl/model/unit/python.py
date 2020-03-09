from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr


@unit_type("python_package")
@attr.s(kw_only=True, frozen=True)
class PythonPackageUnit(Unit):
    filename = pulp_attrib(type=str, pulp_field="filename")
    name = pulp_attrib(type=str, pulp_field="name")
    sha512sum = pulp_attrib(type=str, pulp_field="_checksum")

    content_type_id = pulp_attrib(
        default="python_package", type=str, pulp_field="_content_type_id"
    )
