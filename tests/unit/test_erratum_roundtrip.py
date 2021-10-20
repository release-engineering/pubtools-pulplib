import json
import os

from pubtools.pulplib import Unit, ErratumUnit


def test_erratum_roundtrip(data_path):
    """ErratumUnit from/to data are (approximately) the inverse of each other."""

    with open(os.path.join(data_path, "sample-erratum.json"), "rt") as f:
        original_data = json.load(f)

    # Load it from data
    loaded = Unit.from_data(original_data)

    # Should be this type
    assert isinstance(loaded, ErratumUnit)

    # We've loaded from a dict, now let's try to convert it back
    roundtrip_data = loaded._to_data()

    # What we get back should be *almost* exactly equal to what we fed
    # in, but there are a few minor differences, so massage a bit before
    # comparison...

    # The repo list ends up sorted so there's one canonical representation
    original_data["repository_memberships"].sort()

    # A couple of fields synthesized in the Pulp response don't make it
    # into our model
    del original_data["_id"]
    del original_data["_last_updated"]
    del original_data["_href"]
    del original_data["children"]

    assert roundtrip_data == original_data
