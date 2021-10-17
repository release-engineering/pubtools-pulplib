import six

from pubtools.pulplib._impl import compat_attr as attr


# attr metadata private key for mapping between PulpObject attr and the corresponding
# field in Pulp (if it exists)
PULP2_FIELD = "_pubtools.pulplib.pulp2_field"

# attr metadata private key indicating whether a field is part of the unit_key.
PULP2_UNIT_KEY = "_pubtools.pulplib.pulp2_unit_key"

# attr metadata private key for converting from a pulp2 representation and a Python
# object.
# Why not using attr.ib built-in 'converter'?  Because that makes it public API,
# i.e. clients could construct PulpObject subclasses directly with Pulp data.
# This is not desired, better to have all Pulp conversion logic strictly hidden behind
# from_data methods.
PULP2_PY_CONVERTER = "_pubtools.pulplib.pulp2_to_py_converter"

# Inverse of the above: converter for Python value into Pulp2 value.
PY_PULP2_CONVERTER = "_pubtools.pulplib.py_to_pulp2_converter"


def pulp_attrib(
    pulp_field=None,
    pulp_py_converter=None,
    py_pulp_converter=None,
    unit_key=None,
    **kwargs
):
    """Drop-in replacement for attr.ib with added features:

    - applies a validator based on type automatically
    - supports pulplib-specific metadata via extra keyword arguments
    """
    metadata = kwargs.get("metadata") or {}

    if pulp_field:
        metadata[PULP2_FIELD] = pulp_field

    if pulp_py_converter:
        metadata[PULP2_PY_CONVERTER] = pulp_py_converter

    if py_pulp_converter:
        metadata[PY_PULP2_CONVERTER] = py_pulp_converter

    if unit_key is not None:
        metadata[PULP2_UNIT_KEY] = unit_key

    if "type" in kwargs:
        # As a convenience, you may define string types as type=str
        # on any python version, but what you'll actually get is
        # whatever's the primary string type (e.g. basestr on py2)
        if kwargs["type"] is str:
            kwargs["type"] = six.string_types[0]

        # If you haven't defined a validator, you get one automatically
        # for your requested type
        if "validator" not in kwargs:
            kwargs["validator"] = attr.validators.optional(
                attr.validators.instance_of(kwargs["type"])
            )

    kwargs["metadata"] = metadata
    return attr.ib(**kwargs)
