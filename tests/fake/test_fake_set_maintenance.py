import json
import os

import pytest

from pubtools.pulplib import (
    FakeController,
    Repository,
    FileRepository,
    MaintenanceReport,
    InvalidDataException,
)

MaintenanceReport._OWNER = "ContentDelivery"


def test_set_maintenance():

    controller = FakeController()

    maintain_repo = FileRepository(id="redhat-maintenance")

    controller.insert_repository(maintain_repo)
    # now the maintenance repo is empty

    client = controller.client

    report = client.get_maintenance_report().result()

    assert isinstance(report, MaintenanceReport)
    # return an empty report
    assert report.entries == ()
    # there's no entries in the report

    report = report.add(repo_ids=["repo1", "repo2"])
    client.set_maintenance(report).result()
    # add entries to report and set maintenance

    # upload_file and publish should be called once each
    assert len(controller.upload_history) == 1
    assert len(controller.publish_history) == 1

    # get_maintenance_report should give a report object
    report = client.get_maintenance_report().result()
    assert report.last_updated_by == "ContentDelivery"
    assert len(report.entries) == 2

    report = report.remove(repo_ids=["repo1"], owner="jazhang@hostname")
    client.set_maintenance(report).result()

    # the report in repo should have updated
    report = client.get_maintenance_report().result()
    assert report.last_updated_by == "jazhang@hostname"
    assert len(report.entries) == 1
    assert report.entries[0].repository_id == "repo2"


def test_load_invalid_report_raise_exception():
    controller = FakeController()

    client = controller.client
    report = {
        "last_updated": "2019-08-15T14:21:1211",  # invalid timestamp
        "last_updated_by": "pubtools.pulplib",
        "repos": {
            "repo1": {
                "message": "Maintenance Mode Enabled",
                "owner": "pubtools.pulplib",
                "started": "2019-08-15T14:21:12Z",
            }
        },
    }
    client._maintenance_report = json.dumps(report, indent=4, sort_keys=True)

    with pytest.raises(InvalidDataException):
        client.get_maintenance_report()
