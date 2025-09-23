import datetime
import pytest

from pubtools.pulplib import RpmUnit


@pytest.fixture(name="rpm_data")
def rpm_data():
    return {
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
        "repodata": {
            "filelists": """<package arch='x86_64' name='bash' pkgid='123'>\n
                <version epoch='0' rel='1' ver='4.0' />\n
                <file>/usr/bin/bash</file>\n
                <file>/usr/bin/some/script.sh</file>\n
                <file>/usr/bin/some/script-provided.py</file>\n
                <file type='dir'>/usr/bin/some</file>\n
                </package>"""
        },
        "files": {
            "file": [
                "/usr/bin/some/script.sh",
                "/usr/bin/some/script-provided.py",
            ],
        },
    }


def test_user_metadata_fields(rpm_data):
    """RpmUnit.from_data parses pulp_user_metadata fields OK"""

    loaded = RpmUnit.from_data(rpm_data)

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
        files=[
            "/usr/bin/some/script.sh",
            "/usr/bin/some/script-provided.py",
        ],
        filelist=[
            "/usr/bin/bash",
            "/usr/bin/some/script.sh",
            "/usr/bin/some/script-provided.py",
        ],
    )


def test_user_metadata_fields_malformed_xml(rpm_data):
    """Malformed repodata.filelists is ignored"""
    # Update the rpm_data fixture to contain malformed xml
    rpm_data["repodata"][
        "filelists"
    ] = """
        <package arch='x86_64' name='bash' pkgid='123'>\n
        <version epoch='0' rel='1' ver='4.0' />\n
        <file>/usr/bin/bash
        <file type='dir'>/usr/bin/some</file>\n
        </package>
    """
    loaded = RpmUnit.from_data(rpm_data)

    # There is no filelist field in the loaded RpmUnit
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
        files=[
            "/usr/bin/some/script.sh",
            "/usr/bin/some/script-provided.py",
        ],
    )


def test_repr_no_defaults():
    """Verify that repr only shows those fields with non-default values."""

    u = RpmUnit(name="bash", version="4.0", release="1", arch="x86_64")

    assert repr(u) == "RpmUnit(name='bash', version='4.0', release='1', arch='x86_64')"


def test_rpm_unit_get_files(rpm_data):
    loaded = RpmUnit.from_data(rpm_data)

    result = loaded.get_files()

    assert result == [
        "/usr/bin/bash",
        "/usr/bin/some/script-provided.py",
        "/usr/bin/some/script.sh",
    ]
