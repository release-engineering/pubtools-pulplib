import json

import pytest

from pubtools.pulplib import (
    FakeController,
    Repository,
    FileRepository,
    MaintenanceReport,
    InvalidDataException,
)


def test_set_maintenance():

    controller = FakeController()

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2")
    maintain_repo = FileRepository(id="redhat-maintenance")

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)
    controller.insert_repository(maintain_repo)
    # now the maintenance repo is empty

    client = controller.client

    regex = "repo1"

    # set maintenance to off doesn't do anything
    assert client.set_maintenance(regex, enable=False) == None

    # set repo1 to maintenance, a report should be generated and uploaded
    report = client.set_maintenance(regex)

    report = json.loads(report)

    assert report["last_updated_by"] == "Content Delivery"
    assert "repo1" in report["repos"].keys()
    assert "repo2" not in report["repos"].keys()
    assert report["repos"]["repo1"]["message"] == "Maintenance mode is enabled"

    # upload_file and publish should be called once each
    assert len(controller.upload_history) == 1
    assert len(controller.publish_history) == 1

    # get_maintenance_report should give a report object
    report = client.get_maintenance_report()
    assert isinstance(report, MaintenanceReport)
    assert report.last_updated_by == "Content Delivery"

    # unset repo1 to maintenance
    report = client.set_maintenance(regex, enable=False)

    report = json.loads(report)
    assert report["repos"] == {}

    # the report in repo should have updated
    report = client.get_maintenance_report()
    assert report.repos == {}


def test_load_invalid_report_raise_exception():
    controller = FakeController()

    client = controller.client
    report = {
        "last_updated": "2019-08-15T14:21:121Z",
        "last_updated_by": "Content Delivery",
        "repos": {
            "repo1": {
                "message": "Maintenance Mode Enabled",
                "owner": "Content Delivery",
                "started": "2019-08-15T14:21:12Z",
            }
        },
    }
    client._maintenance_report = json.dumps(report, indent=4, sort_keys=True)

    with pytest.raises(InvalidDataException):
        client.get_maintenance_report()
