from .base import Unit, unit_type

from ..attr import pulp_attrib
from ... import compat_attr as attr
from ..frozenlist import frozenlist_or_none_converter


@unit_type("modulemd")
@attr.s(kw_only=True, frozen=True)
class ModulemdUnit(Unit):
    """A :class:`~pubtools.pulplib.Unit` representing a modulemd document.

    .. versionadded:: 1.5.0
    """

    name = pulp_attrib(type=str, pulp_field="name")
    """The name of this module.

    Example: the name of javapackages-tools:201801:20180813043155:dca7b4a4:aarch64
    is "javapackages-tools".
    """

    stream = pulp_attrib(type=str, pulp_field="stream")
    """The stream of this module.

    Example: the stream of javapackages-tools:201801:20180813043155:dca7b4a4:aarch64
    is "201801".
    """

    version = pulp_attrib(type=int, pulp_field="version")
    """The version of this module.

    Example: the version of javapackages-tools:201801:20180813043155:dca7b4a4:aarch64
    is 20180813043155.
    """

    context = pulp_attrib(type=str, pulp_field="context")
    """The context of this module.

    Example: the context of javapackages-tools:201801:20180813043155:dca7b4a4:aarch64
    is "dca7b4a4".
    """

    arch = pulp_attrib(type=str, pulp_field="arch")
    """The architecture of this module.

    Example: the arch of javapackages-tools:201801:20180813043155:dca7b4a4:aarch64
    is "aarch64.
    """

    content_type_id = pulp_attrib(
        default="modulemd", type=str, pulp_field="_content_type_id"
    )

    repository_memberships = pulp_attrib(
        default=None,
        type=list,
        converter=frozenlist_or_none_converter,
        pulp_field="repository_memberships",
    )
    """IDs of repositories containing the unit, or ``None`` if this information is unavailable.

    .. versionadded:: 2.6.0
    """
