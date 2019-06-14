import os
import logging

import yaml
import jsonschema


LOG = logging.getLogger("pubtools.pulplib")


def load_schema(basename, definition=None):
    """Load a JSON schema file from YAML.

    If definition is given, a subschema can be referenced.
    """

    filename = os.path.join(os.path.dirname(__file__), "%s.yaml" % basename)
    with open(filename) as file:
        schema = yaml.safe_load(file)

    if definition:
        schema = schema["definitions"][definition]

    return schema
