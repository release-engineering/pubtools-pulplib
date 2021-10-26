import os
from io import BytesIO

from xml.parsers.expat import ExpatError

import pytest

from pubtools.pulplib import FakeController, YumRepository


def test_can_upload_comps(data_path):
    """repo.upload_comps_xml() succeeds with fake client."""

    xml_path = os.path.join(data_path, "sample-comps.xml")

    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    upload_f = repo1.upload_comps_xml(xml_path)

    # Upload should complete successfully.
    tasks = upload_f.result()

    # At least one task.
    assert tasks

    # Every task should have succeeded.
    for t in tasks:
        assert t.succeeded

    # If I now search for all content...
    units_all = list(client.search_content())

    # There should still be nothing, as the fake does not actually store
    # and reproduce comps-related units.
    assert units_all == []


def test_upload_comps_error():
    """repo.upload_comps_xml() raises with fake client when given invalid input."""
    xml = BytesIO(b"Oops not valid")

    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    with pytest.raises(ExpatError):
        repo1.upload_comps_xml(xml)
