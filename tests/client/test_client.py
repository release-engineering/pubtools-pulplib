import logging
import datetime
import json
import pytest

from mock import patch

from more_executors.futures import f_return

from pubtools.pulplib import (
    Client,
    Criteria,
    Matcher,
    Repository,
    PulpException,
    MaintenanceReport,
    Task,
    Distributor,
    RpmUnit,
)


def test_can_construct(requests_mocker):
    """A client instance can be constructed with URL alone."""
    client = Client("https://pulp.example.com/")


def test_can_construct_with_throttle_arg(requests_mocker):
    """
    A client instance can be constructed with task_throttle arg that is passed
    to Client._task_executor
    """
    throttle_count = 42
    client = Client("https://pulp.example.com/", task_throttle=throttle_count)
    assert client._task_executor._delegate._throttle() == throttle_count


def test_can_construct_with_session_args(requests_mocker):
    """A client instance can be constructed with requests.Session kwargs."""
    client = Client("https://pulp.example.com/", auth=("x", "y"), verify=False)


def test_construct_raises_on_bad_args(requests_mocker):
    """A client instance cannot be constructed with unexpected args."""
    with pytest.raises(TypeError):
        client = Client("https://pulp.example.com/", whatever="foobar")


def test_search_raises_on_bad_args(client, requests_mocker):
    """search_repository raises TypeError if passed something other than Criteria"""
    with pytest.raises(TypeError):
        client.search_repository("oops, not valid criteria")


def test_can_search(client, requests_mocker):
    """search_repository issues /search/ POST requests as expected."""
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/",
        json=[{"id": "repo1"}, {"id": "repo2"}],
    )

    repos = client.search_repository()

    # It should have returned the repos as objects
    assert sorted(repos) == [Repository(id="repo1"), Repository(id="repo2")]

    # It should have issued only a single search
    assert requests_mocker.call_count == 1


def test_client_lifecycle(client, requests_mocker):
    """Client is usable in with statement"""

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/",
        json=[{"id": "repo1"}],
    )

    client = Client("https://pulp.example.com")
    with client:
        # This should work OK
        assert client.search_repository().result()

    # But after end of 'with' statement, it should be shut down
    with pytest.raises(RuntimeError) as excinfo:
        client.search_repository()

    assert "cannot schedule new futures after shutdown" in str(excinfo.value)


def test_can_search_distributor(client, requests_mocker):
    """search_distributor issues distributors/search POST request as expected."""
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/distributors/search/",
        json=[
            {
                "id": "yum_distributor",
                "distributor_type_id": "yum_distributor",
                "repo_id": "test_rpm",
                "config": {"relative_url": "relative/path"},
            },
            {
                "id": "cdn_distributor",
                "distributor_type_id": "rpm_rsync_distributor",
                "config": {"relative_url": "relative/path"},
            },
        ],
    )

    distributors_f = client.search_distributor()
    distributors = [dist for dist in distributors_f.result().as_iter()]
    # distributor objects are returned
    assert sorted(distributors) == [
        Distributor(
            id="cdn_distributor",
            type_id="rpm_rsync_distributor",
            relative_url="relative/path",
        ),
        Distributor(
            id="yum_distributor",
            type_id="yum_distributor",
            repo_id="test_rpm",
            relative_url="relative/path",
        ),
    ]
    # api is called once
    assert requests_mocker.call_count == 1


def test_can_search_distributors_with_relative_url(client, requests_mocker):
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/distributors/search/",
        json=[
            {
                "id": "yum_distributor",
                "distributor_type_id": "yum_distributor",
                "repo_id": "test_rpm",
                "config": {"relative_url": "relative/path"},
            },
            {
                "id": "cdn_distributor",
                "distributor_type_id": "rpm_rsync_distributor",
                "config": {"relative_url": "relative/path"},
            },
        ],
    )

    crit = Criteria.with_field("relative_url", Matcher.regex("relative/path"))
    distributors_f = client.search_distributor(crit)

    distributors = [dist for dist in distributors_f.result()]

    # distributor objects are returned
    assert sorted(distributors) == [
        Distributor(
            id="cdn_distributor",
            type_id="rpm_rsync_distributor",
            relative_url="relative/path",
        ),
        Distributor(
            id="yum_distributor",
            type_id="yum_distributor",
            repo_id="test_rpm",
            relative_url="relative/path",
        ),
    ]
    # api is called once
    assert requests_mocker.call_count == 1


def test_search_retries(client, requests_mocker, caplog):
    """search_repository retries operations on failure."""
    logging.getLogger().setLevel(logging.WARNING)
    caplog.set_level(logging.WARNING)

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/",
        [
            {"status_code": 413},
            {"status_code": 500},
            # Let's also mix in something which isn't valid json
            {"text": '{"not-valid-json": '},
            {"json": [{"id": "repo1"}]},
        ],
    )

    repos_f = client.search_repository()

    repos = [r for r in repos_f]

    # It should have found the repo
    assert repos == [Repository(id="repo1")]

    # But would have needed several attempts
    assert requests_mocker.call_count == 4

    # And those retries should have been logged
    messages = caplog.messages
    assert len(messages) == 3

    # Messages have full exception detail. Just check the first line.
    lines = [m.splitlines()[0] for m in messages]

    assert lines[0].startswith("Retrying due to error: 413")
    assert lines[0].endswith(" [1/6]")
    assert lines[1].startswith("Retrying due to error: 500")
    assert lines[1].endswith(" [2/6]")
    assert lines[2].startswith("Retrying due to error:")
    assert lines[2].endswith(" [3/6]")

    # Retry logs should have the pulp-retry event attached.
    assert caplog.records[-1].event == {"type": "pulp-retry"}


def test_search_can_paginate(client, requests_mocker):
    """search_repository implicitly paginates the search as needed."""
    client._PAGE_SIZE = 10

    expected_repos = []
    responses = []
    current_response = []
    for i in range(0, 997):
        repo_id = "repo-%s" % i
        expected_repos.append(Repository(id=repo_id))
        current_response.append({"id": repo_id})
        if len(current_response) == client._PAGE_SIZE:
            responses.append({"json": current_response})
            current_response = []

    responses.append({"json": current_response})

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/", responses
    )

    repos_f = client.search_repository()

    repos = [r for r in repos_f.result().as_iter()]

    # It should have returned the repos as objects
    assert sorted(repos) == sorted(expected_repos)

    # It needed to do 100 requests to get all the data
    assert requests_mocker.call_count == 100

    # Requests should have used skip/limit to paginate appropriately.
    # We'll just sample a few of the requests here.
    history = requests_mocker.request_history
    criteria = [h.json()["criteria"] for h in history]
    assert criteria[0] == {"filters": {}, "skip": 0, "limit": 10}
    assert criteria[1] == {"filters": {}, "skip": 10, "limit": 10}
    assert criteria[2] == {"filters": {}, "skip": 20, "limit": 10}
    assert criteria[-1] == {"filters": {}, "skip": 990, "limit": 10}


def test_can_get(client, requests_mocker):
    """get_repository gets a repository (via search)."""
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/",
        json=[{"id": "repo1"}],
    )

    repo_f = client.get_repository("repo1")

    # It should have returned the expected repo
    assert repo_f.result() == Repository(id="repo1")

    # It should have issued only a single search
    assert requests_mocker.call_count == 1

    # The search should have used these filters
    assert requests_mocker.last_request.json()["criteria"].get("filters") == {
        "id": {"$eq": "repo1"}
    }


def test_get_missing(client, requests_mocker):
    """get_repository raises meaningful exception if repo is missing"""

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/", json=[]
    )

    repo_f = client.get_repository("repo1")

    # It should raise
    with pytest.raises(PulpException) as error:
        repo_f.result()

    # It should explain the problem
    assert "repo1 was not found" in str(error.value)


def test_can_get_maintenance_report(client, requests_mocker):
    maintenance_report = {
        "last_updated": "2019-08-15T14:21:12Z",
        "last_updated_by": "Content Delivery",
        "repos": {
            "repo1": {
                "message": "Maintenance Mode Enabled",
                "owner": "Content Delivery",
                "started": "2019-08-15T14:21:12Z",
            }
        },
    }
    requests_mocker.get(
        "https://pulp.example.com/pulp/isos/redhat-maintenance/repos.json",
        json=maintenance_report,
    )

    report = client.get_maintenance_report().result()

    assert requests_mocker.call_count == 1
    assert isinstance(report, MaintenanceReport)
    assert report.last_updated_by == "Content Delivery"
    assert report.last_updated == datetime.datetime(2019, 8, 15, 14, 21, 12)
    assert report.entries[0].message == "Maintenance Mode Enabled"


def test_non_maintenance_report(client, requests_mocker):
    requests_mocker.get(
        "https://pulp.example.com/pulp/isos/redhat-maintenance/repos.json",
        text="Not Found",
        status_code=404,
    )

    report = client.get_maintenance_report().result()
    assert report.last_updated_by is None
    assert report.entries == []


def test_get_invalid_maintenance_file(client, requests_mocker, caplog):
    requests_mocker.get(
        "https://pulp.example.com/pulp/isos/redhat-maintenance/repos.json",
        text='{"not-valid-json": ',
    )
    with pytest.raises(Exception):
        client.get_maintenance_report().result()

    messages = caplog.messages
    assert len(messages) == 5

    # Messages have full exception detail. Just check the first line.
    lines = [m.splitlines()[0] for m in messages]

    assert lines[-1].startswith("Retrying due to error:")
    assert lines[-1].endswith(" [5/6]")


def test_set_maintenance(client, requests_mocker):
    maintenance_report = {
        "last_updated": "2019-08-15T14:21:12Z",
        "last_updated_by": "pubtools.pulplib",
        "repos": {
            "repo1": {
                "message": "Maintenance Mode Enabled",
                "owner": "pubtools.pulplib",
                "started": "2019-08-15T14:21:12Z",
            }
        },
    }
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/",
        [{"json": [{"id": "redhat-maintenance", "notes": {"_repo-type": "iso-repo"}}]}],
    )

    report = MaintenanceReport._from_data(maintenance_report)

    with patch("pubtools.pulplib.FileRepository.upload_file") as mocked_upload:
        with patch("pubtools.pulplib.Repository.publish") as mocked_publish:
            upload_task = Task(id="upload-task", completed=True, succeeded=True)
            publish_task = [Task(id="publish-task", completed=True, succeeded=True)]

            mocked_upload.return_value = f_return(upload_task)
            mocked_publish.return_value = f_return(publish_task)

            # set_maintenance.result() should return whatever publish.result() returns
            assert client.set_maintenance(report).result() is publish_task

    # upload_file should be called with (file_obj, 'repos.json')
    args = mocked_upload.call_args
    report_file = args[0][0]
    report = MaintenanceReport()._from_data(json.loads(report_file.read()))

    assert len(report.entries) == 1
    assert report.entries[0].repo_id == "repo1"
    assert report.last_updated_by == "pubtools.pulplib"

    # search repo, upload and publish should be called once each
    assert requests_mocker.call_count == 1
    assert mocked_publish.call_count == 1
    assert mocked_upload.call_count == 1


RPM_TEST_UNITS = [
    {
        "_content_type_id": "rpm",
        "_id": "d4633746-1ccc-4d85-9733-0007c87e0724",
        "checksum": "1c4baac658fd56e6ec9cca37f440a4bd8c9c0b02a21f41b30b8ea17b402a1907",
        "checksums": {
            "sha1": "ca995eb1a635c97393466f67aaec8e9e753b8ed5",
            "sha256": "1c4baac658fd56e6ec9cca37f440a4bd8c9c0b02a21f41b30b8ea17b402a1907",
        },
        "arch": "i386",
        "epoch": "0",
        "name": "gnu-efi-debuginfo",
        "release": "1.1",
        "repository_memberships": ["fake-repository-id-1", "fake-repository-id-2"],
        "sourcerpm": "gnu-efi-3.0c-1.1.src.rpm",
        "version": "3.0c",
    },
    {
        "_content_type_id": "rpm",
        "_id": "bd2e0321-48f6-4997-a5dc-e73c771bc17d",
        "checksum": "4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
        "checksums": {
            "sha256": "4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679"
        },
        "arch": "ia64",
        "epoch": "0",
        "name": "glibc-headers",
        "release": "2.57.el4.1",
        "repository_memberships": ["fake-repository-id-3"],
        "sourcerpm": "glibc-2.3.4-2.57.el4.1.src.rpm",
        "version": "2.3.4",
    },
]

SRPM_TEST_UNITS = [
    {
        "_content_type_id": "srpm",
        "_id": "bd2e0321-48f6-4997-a5dc-e73c771bc17d",
        "checksum": "4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
        "checksums": {
            "sha256": "4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679"
        },
        "arch": "src",
        "epoch": "0",
        "name": "glibc",
        "release": "2.57.el4.1",
        "repository_memberships": ["fake-repository-id-3"],
        "sourcerpm": None,
        "version": "2.3.4",
    }
]


def test_can_search_content(client, requests_mocker):
    """search_content basic call"""
    requests_mocker.get(
        "https://pulp.example.com/pulp/api/v2/plugins/types/",
        json=[{"id": "rpm"}, {"id": "srpm"}],
    )
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/content/units/rpm/search/",
        json=RPM_TEST_UNITS,
    )
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/content/units/srpm/search/",
        json=SRPM_TEST_UNITS,
    )

    units = client.search_content()

    # It should have returned the repos as objects
    assert sorted(units) == [
        RpmUnit(
            content_type_id="srpm",
            sha256sum="4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
            arch="src",
            epoch="0",
            name="glibc",
            release="2.57.el4.1",
            repository_memberships=["fake-repository-id-3"],
            sourcerpm=None,
            version="2.3.4",
        ),
        RpmUnit(
            sha256sum="4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
            arch="ia64",
            epoch="0",
            name="glibc-headers",
            release="2.57.el4.1",
            repository_memberships=["fake-repository-id-3"],
            sourcerpm="glibc-2.3.4-2.57.el4.1.src.rpm",
            version="2.3.4",
        ),
        RpmUnit(
            sha1sum="ca995eb1a635c97393466f67aaec8e9e753b8ed5",
            sha256sum="1c4baac658fd56e6ec9cca37f440a4bd8c9c0b02a21f41b30b8ea17b402a1907",
            arch="i386",
            epoch="0",
            name="gnu-efi-debuginfo",
            release="1.1",
            repository_memberships=["fake-repository-id-1", "fake-repository-id-2"],
            sourcerpm="gnu-efi-3.0c-1.1.src.rpm",
            version="3.0c",
        ),
    ]

    # 3 requests, 1 for server type_ids, 1 for rpm, 1 for srpm
    assert requests_mocker.call_count == 3


def test_can_search_content_invalid_criteria(client, requests_mocker):
    """search_content issues /search/ POST requests as expected."""
    requests_mocker.get(
        "https://pulp.example.com/pulp/api/v2/plugins/types/",
        json=[{"id": "rpm"}, {"id": "srpm"}],
    )
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/content/units/rpm/search/",
        json=RPM_TEST_UNITS,
    )

    with pytest.raises(ValueError) as e:
        _ = client.search_content(Criteria.with_field("_content_type_id", "foobar"))
    assert str(e.value) == "Content type: foobar is not supported by server"

    assert requests_mocker.call_count == 1


def test_can_search_content_pagination(client, requests_mocker):
    """search_content pagination should search only for types that returns non-empty"""
    requests_mocker.get(
        "https://pulp.example.com/pulp/api/v2/plugins/types/",
        json=[{"id": "rpm"}, {"id": "srpm"}],
    )
    requests_mocker.register_uri(
        "POST",
        "https://pulp.example.com/pulp/api/v2/content/units/rpm/search/",
        [{"json": [RPM_TEST_UNITS[0]]}, {"json": [RPM_TEST_UNITS[1]]}, {"json": []}],
    )
    requests_mocker.register_uri(
        "POST",
        "https://pulp.example.com/pulp/api/v2/content/units/srpm/search/",
        [{"json": SRPM_TEST_UNITS}, {"json": []}],
    )
    client._PAGE_SIZE = 1

    units = client.search_content()

    # It should have returned the repos as objects
    assert sorted(units) == [
        RpmUnit(
            content_type_id="srpm",
            sha256sum="4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
            arch="src",
            epoch="0",
            name="glibc",
            release="2.57.el4.1",
            repository_memberships=["fake-repository-id-3"],
            sourcerpm=None,
            version="2.3.4",
        ),
        RpmUnit(
            sha256sum="4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
            arch="ia64",
            epoch="0",
            name="glibc-headers",
            release="2.57.el4.1",
            repository_memberships=["fake-repository-id-3"],
            sourcerpm="glibc-2.3.4-2.57.el4.1.src.rpm",
            version="2.3.4",
        ),
        RpmUnit(
            sha1sum="ca995eb1a635c97393466f67aaec8e9e753b8ed5",
            sha256sum="1c4baac658fd56e6ec9cca37f440a4bd8c9c0b02a21f41b30b8ea17b402a1907",
            arch="i386",
            epoch="0",
            name="gnu-efi-debuginfo",
            release="1.1",
            repository_memberships=["fake-repository-id-1", "fake-repository-id-2"],
            sourcerpm="gnu-efi-3.0c-1.1.src.rpm",
            version="3.0c",
        ),
    ]

    # 3 requests, 1 for server type_ids, 1 for rpm, 1 for srpm
    assert [h.url for h in requests_mocker.request_history].count(
        "https://pulp.example.com/pulp/api/v2/content/units/rpm/search/"
    ) == 3
    assert [h.url for h in requests_mocker.request_history].count(
        "https://pulp.example.com/pulp/api/v2/content/units/srpm/search/"
    ) == 2
