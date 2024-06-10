from .. import compat_attr as attr

optional = attr.validators.optional
instance_of = attr.validators.instance_of


@attr.s(kw_only=True, frozen=True, repr=True)
class CopyOptions(object):
    """Options influencing a call to
    :meth:`~pubtools.pulplib.Client.copy_content`.
    """

    require_signed_rpms = attr.ib(
        type=bool, default=None, validator=optional(instance_of(bool))
    )
    """Whether to require signatures on all RPMs in the copy.

    In order to copy unsigned RPMs between repositories, it is generally
    necessary to set this flag to ``False``. Unsigned RPMs may otherwise
    be silently omitted from the copy.
    """
