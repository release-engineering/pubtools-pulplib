from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr


@unit_type("modulemd_defaults")
@attr.s(kw_only=True, frozen=True)
class ModulemdDefaultsUnit(Unit):
    """A :class:`~pubtools.pulplib.Unit` representing a modulemd_defaults document.

    .. versionadded:: 2.4.0
    """

    name = pulp_attrib(type=str, pulp_field="name")
    """The name of this modulemd defaults unit"""

    stream = pulp_attrib(type=str, pulp_field="stream")
    """The stream of this modulemd defaults unit"""

    repo_id = pulp_attrib(type=str, pulp_field="repo_id")
    """The repository ID bound to this modulemd defaults unit"""

    profiles = pulp_attrib(pulp_field="profiles")
    """The profiles of this modulemd defaults unit.

    The type for this attribute is omitted to allow for either dict or None.
    """
