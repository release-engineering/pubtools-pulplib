from pubtools.pulplib._impl import compat_attr as attr


# attr metadata private key for mapping between PulpObject attr and the corresponding
# field in Pulp (if it exists)
PULP2_FIELD = "_pubtools.pulplib.pulp2_field"

# attr metadata private key for converting from a pulp2 representation and a Python
# object.
# Why not using attr.ib built-in 'converter'?  Because that makes it public API,
# i.e. clients could construct PulpObject subclasses directly with Pulp data.
# This is not desired, better to have all Pulp conversion logic strictly hidden behind
# from_data methods.
PULP2_PY_CONVERTER = "_pubtools.pulplib.pulp2_to_py_converter"


# make usage of the above less ugly
def pulp_attrib(pulp_field=None, pulp_py_converter=None, **kwargs):
    metadata = kwargs.get("metadata") or {}

    if pulp_field:
        metadata[PULP2_FIELD] = pulp_field

    if pulp_py_converter:
        metadata[PULP2_PY_CONVERTER] = pulp_py_converter

    kwargs["metadata"] = metadata
    return attr.ib(**kwargs)
