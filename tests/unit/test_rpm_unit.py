import datetime

from pubtools.pulplib import RpmUnit


def test_user_metadata_fields():
    """RpmUnit.from_data parses pulp_user_metadata fields OK"""

    loaded = RpmUnit.from_data(
        {
            "_content_type_id": "rpm",
            "name": "bash",
            "epoch": "0",
            "filename": "bash-x86_64.rpm",
            "version": "4.0",
            "release": "1",
            "arch": "x86_64",
            "pulp_user_metadata": {
                "cdn_path": "/some/path/to/my.rpm",
                "cdn_published": "2021-04-01T01:08:26",
            },
        }
    )

    assert loaded == RpmUnit(
        name="bash",
        epoch="0",
        filename="bash-x86_64.rpm",
        version="4.0",
        release="1",
        arch="x86_64",
        content_type_id="rpm",
        cdn_path="/some/path/to/my.rpm",
        cdn_published=datetime.datetime(2021, 4, 1, 1, 8, 26),
    )


def test_repr_no_defaults():
    """Verify that repr only shows those fields with non-default values."""

    u = RpmUnit(name="bash", version="4.0", release="1", arch="x86_64")

    assert repr(u) == "RpmUnit(name='bash', version='4.0', release='1', arch='x86_64')"
