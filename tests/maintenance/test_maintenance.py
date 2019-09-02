import pytest

from pubtools.pulplib import MaintenanceReport, MaintenanceEntry, InvalidDataException

MaintenanceReport._OWNER = "ContentDelivery"


def test_create_report_with_duplicate_entries():
    entry = MaintenanceEntry(repo_id="repo1")
    dup_entry = MaintenanceEntry(repo_id="repo1")

    with pytest.raises(ValueError):
        MaintenanceReport(entries=(entry, dup_entry))


def test_add_entry_existed():
    entry = MaintenanceEntry(
        repo_id="repo1",
        owner="someone",
        message="Enabled",
        started="2019-08-15T14:21:12Z",
    )

    report = MaintenanceReport(entries=(entry,))

    report = report.add(repo_ids=["repo1"], owner="someone_else")
    # add duplicated entry to report

    assert len(report.entries) == 1
    assert report.entries[0].owner == "someone_else"


def test_load_invalid_report_raise_exception():
    data = {
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

    with pytest.raises(InvalidDataException):
        MaintenanceReport._from_data(data)


def test_create_export_report():
    data = {
        "last_updated": "2019-08-15T14:21:12Z",  # invalid timestamp
        "last_updated_by": "pubtools.pulplib",
        "repos": {
            "repo1": {
                "message": "Maintenance Mode Enabled",
                "owner": "pubtools.pulplib",
                "started": "2019-08-15T14:21:12Z",
            }
        },
    }

    report = MaintenanceReport._from_data(data)

    exported_data = report._export_dict()

    assert data == exported_data


def test_report_add_remove():
    data = {
        "last_updated": "2019-08-15T14:21:12Z",  # invalid timestamp
        "last_updated_by": "pubtools.pulplib",
        "repos": {
            "repo1": {
                "message": "Maintenance Mode Enabled",
                "owner": "pubtools.pulplib",
                "started": "2019-08-15T14:21:12Z",
            }
        },
    }

    report = MaintenanceReport._from_data(data)

    report = report.add(repo_ids=["repo2", "repo3"])

    assert len(report.entries) == 3
    assert report.last_updated_by == "ContentDelivery"

    report = report.remove(repo_ids=["repo1", "repo2"], owner="jazhang")

    assert len(report.entries) == 1
    assert report.last_updated_by == "jazhang"
