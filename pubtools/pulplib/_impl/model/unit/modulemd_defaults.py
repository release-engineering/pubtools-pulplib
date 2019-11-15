from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr


@unit_type("modulemd")
@attr.s(kw_only=True, frozen=True)
class ModulemdDefaultsUnit(Unit):
    """A :class:`~pubtools.pulplib.Unit` representing a modulemd_defaults document.

    .. versionadded:: 1.5.0
    """

    name = pulp_attrib(type=str, pulp_field="name")
    """The name of this modulemd defaults unit.

    Example: the name of ant:rhel-8-for-aarch64-appstream-htb-rpms is "ant".
    """

    stream = pulp_attrib(type=str, pulp_field="stream")
    """The stream of this modulemd defaults unit.

    Example: the stream of ant:rhel-8-for-aarch64-appstream-htb-rpms is "1.10".
    """

    repository_id = pulp_attrib(type=str, pulp_field="repo_id")
    """The repository ID bound to this modulemd defaults unit.

    Example: the repo_id of ant:rhel-8-for-aarch64-appstream-htb-rpms
    is "rhel-8-for-aarch64-appstream-htb-rpms".
    """
