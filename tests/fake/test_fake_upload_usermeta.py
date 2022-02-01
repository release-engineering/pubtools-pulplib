import datetime
import os

import pytest

from pubtools.pulplib import FakeController, FileRepository, YumRepository


def test_upload_file_meta_wrong_fields(tmpdir):
    controller = FakeController()

    controller.insert_repository(FileRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    somefile = tmpdir.join("some-file.txt")
    somefile.write(b"there is some binary data:\x00\x01\x02")

    # This should immediately give an error
    with pytest.raises(ValueError) as excinfo:
        repo1.upload_file(
            str(somefile), description="My great file", size=48, other="whatever"
        )

    # It should give an indication of the problem
    assert "Not mutable FileUnit field(s): other, size" in str(excinfo.value)


def test_can_upload_file_meta(tmpdir):
    controller = FakeController()

    controller.insert_repository(FileRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    somefile = tmpdir.join("some-file.txt")
    somefile.write(b"there is some binary data:\x00\x01\x02")

    upload_f = repo1.upload_file(
        str(somefile),
        description="My great file",
        cdn_path="/foo/bar.txt",
        version="2.0",
    )

    # The future should resolve successfully
    tasks = upload_f.result()

    # The task should be successful.
    assert tasks[0].succeeded

    # File should now be in repo.
    units_in_repo = list(repo1.search_content())
    assert len(units_in_repo) == 1
    unit = units_in_repo[0]

    # Sanity check we got the right thing.
    assert unit.path == "some-file.txt"

    # Extra fields we passed during upload should be present here.
    assert unit.description == "My great file"
    assert unit.cdn_path == "/foo/bar.txt"
    assert unit.version == "2.0"


def test_can_reupload_file_meta(tmpdir):
    """Can overwrite by uploading same content twice with different metadata."""
    controller = FakeController()

    controller.insert_repository(FileRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    somefile = tmpdir.join("some-file.txt")
    somefile.write(b"there is some binary data:\x00\x01\x02")

    time1 = datetime.datetime(2021, 12, 14, 14, 44, 0)
    time2 = datetime.datetime(2022, 1, 2, 3, 4, 5)

    upload_f = repo1.upload_file(
        str(somefile),
        description="My great file",
        cdn_path="/foo/bar.txt",
        cdn_published=time1,
    )

    # The future should resolve successfully
    tasks = upload_f.result()

    # The task should be successful.
    assert tasks[0].succeeded

    # Now upload again, but with some different values.
    upload_f = repo1.upload_file(
        str(somefile), description="My even better file", cdn_published=time2
    )

    # The future should resolve successfully
    tasks = upload_f.result()

    # The task should be successful.
    assert tasks[0].succeeded

    # File should now be in repo.
    units_in_repo = list(repo1.search_content())

    # Should result in just one unit, as the second upload effectively merges
    # with the existing unit.
    assert len(units_in_repo) == 1
    unit = units_in_repo[0]

    # Sanity check we got the right thing.
    assert unit.path == "some-file.txt"

    # Extra fields should be equal to the values passed in at the most
    # recent upload.
    assert unit.description == "My even better file"
    assert unit.cdn_published == time2

    # cdn_path was provided at the first upload and not the second.
    # In such cases it is expected that the field is wiped out, as you must
    # always provide *all* metadata at once.
    assert unit.cdn_path is None


def test_can_upload_rpm_meta(data_path):
    rpm_path = os.path.join(data_path, "rpms/walrus-5.21-1.noarch.rpm")
    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    to_upload = rpm_path

    upload_f = repo1.upload_rpm(to_upload, cdn_path="/path/to/my-great.rpm")

    # Upload should complete successfully.
    tasks = upload_f.result()

    # At least one task.
    assert tasks

    # Every task should have succeeded.
    for t in tasks:
        assert t.succeeded

    # RPM should now be in repo.
    units_in_repo = list(repo1.search_content())
    assert len(units_in_repo) == 1
    unit = units_in_repo[0]

    # Sanity check we got the right unit.
    assert unit.filename == "walrus-5.21-1.noarch.rpm"

    # Extra fields we passed during upload should be present here.
    assert unit.cdn_path == "/path/to/my-great.rpm"
