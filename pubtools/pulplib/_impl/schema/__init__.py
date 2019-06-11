import os
import logging

import yaml
import jsonschema


LOG = logging.getLogger("pubtools.pulplib")


def load_schema(basename, ref="#"):
    """Load a JSON schema file from YAML.

    If ref is given, a subschema can be referenced.
    For example, ref="#/definitions/foobar" will load the subschema
    "foobar" from the definitions section
    """

    filename = os.path.join(os.path.dirname(__file__), "%s.yaml" % basename)
    with open(filename) as file:
        schema = yaml.safe_load(file)

    resolver = jsonschema.RefResolver.from_schema(schema)
    (resolved_ref, resolved_schema) = resolver.resolve(ref)

    LOG.debug("Resolved %s to %s", ref, resolved_ref)

    return resolved_schema
