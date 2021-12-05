import sys
import os

import pytest

from pubtools.pulplib import FakeController, YumRepoMetadataFileUnit, YumRepository


@pytest.mark.parametrize("use_file_object", [False, True])
def test_can_upload_units(use_file_object, tmpdir):
    """repo.upload_metadata() succeeds with fake client and populates units."""

    testfile = tmpdir.join("testfile")
    testfile.write(b"some bytes")

    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    to_upload = str(testfile)
    if use_file_object:
        to_upload = open(to_upload, "rb")

    upload_f = repo1.upload_metadata(to_upload, "my-metadata-type")

    # Upload should complete successfully.
    tasks = upload_f.result()

    # At least one task.
    assert tasks

    # Every task should have succeeded.
    for t in tasks:
        assert t.succeeded

    # If I now search for content in that repo, or content across all repos...
    units_in_repo = sorted(repo1.search_content().result(), key=lambda u: u.sha256sum)
    units_all = sorted(client.search_content().result(), key=lambda u: u.sha256sum)

    # They should be equal
    assert units_all == units_in_repo

    # And they should be this
    assert units_in_repo == [
        YumRepoMetadataFileUnit(
            data_type="my-metadata-type",
            sha256sum="0d22cdcc10e6d049dbe1af5123d50873fdfc1a4f58306e58cb6241be9472014d",
            content_type_id="yum_repo_metadata_file",
            repository_memberships=["repo1"],
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
        )
    ]


def test_overwrite(tmpdir):
    """repo.upload_metadata() multiple times with same data type overwrites old data."""

    testfile1 = tmpdir.join("testfile1")
    testfile1.write(b"some bytes")
    testfile2 = tmpdir.join("testfile2")
    testfile2.write(b"other bytes")

    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    upload_f = repo1.upload_metadata(str(testfile1), "mdtype1")

    # Upload should complete successfully.
    upload_f.result()

    # It should have uploaded the first file
    assert list(repo1.search_content()) == [
        YumRepoMetadataFileUnit(
            data_type="mdtype1",
            sha256sum="0d22cdcc10e6d049dbe1af5123d50873fdfc1a4f58306e58cb6241be9472014d",
            content_type_id="yum_repo_metadata_file",
            repository_memberships=["repo1"],
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
        )
    ]

    # Now upload different content with same type
    upload_f = repo1.upload_metadata(str(testfile2), "mdtype1")

    # Upload should complete successfully.
    upload_f.result()

    # There should still just be one unit, but with the updated content
    assert list(repo1.search_content()) == [
        YumRepoMetadataFileUnit(
            data_type="mdtype1",
            sha256sum="a3ead5eedad5df82318c51685dbc1c147a36d1ff8584fc82de6b08d0bf63a795",
            content_type_id="yum_repo_metadata_file",
            repository_memberships=["repo1"],
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
        )
    ]

    # Uploading same content as a *different* type should be fine.
    upload_f = repo1.upload_metadata(str(testfile2), "mdtype2")

    # Upload should complete successfully.
    upload_f.result()

    # Now the same content is available as two types.
    assert sorted(repo1.search_content(), key=lambda u: u.data_type) == [
        YumRepoMetadataFileUnit(
            data_type="mdtype1",
            sha256sum="a3ead5eedad5df82318c51685dbc1c147a36d1ff8584fc82de6b08d0bf63a795",
            content_type_id="yum_repo_metadata_file",
            repository_memberships=["repo1"],
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
        ),
        YumRepoMetadataFileUnit(
            data_type="mdtype2",
            sha256sum="a3ead5eedad5df82318c51685dbc1c147a36d1ff8584fc82de6b08d0bf63a795",
            content_type_id="yum_repo_metadata_file",
            repository_memberships=["repo1"],
            unit_id="e6f4590b-9a16-4106-cf6a-659eb4862b21",
        ),
    ]
