import sys

import pytest

from pubtools.pulplib import FakeController, FileRepository, PulpException


def test_can_upload(tmpdir):
    """repo.upload_file() succeeds with fake client and populates upload_history."""
    controller = FakeController()

    controller.insert_repository(FileRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    somefile = tmpdir.join("some-file.txt")
    somefile.write(b"there is some binary data:\x00\x01\x02")

    upload_f = repo1.upload_file(str(somefile))

    # The future should resolve successfully
    tasks = upload_f.result()

    # The task should be successful.
    assert tasks[0].succeeded

    # The change should be reflected in the controller's upload history
    history = controller.upload_history

    digest = "fad3fc1e6d583b2003ec0a5273702ed8fcc2504271c87c40d9176467ebe218cb"
    assert len(history) == 1
    assert history[0].repository == repo1
    assert history[0].tasks == tasks
    assert history[0].name == somefile.basename
    assert history[0].sha256 == digest


def test_upload_nonexistent_file_raises():
    """repo.upload_file() with nonexistent file fails with fake client"""
    controller = FakeController()

    controller.insert_repository(FileRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    # If file's not found, Python 2 raises IOError and Python 3 raises
    # FileNotFoundError. The latter one is not defined in Python 2.
    if sys.version_info < (3,):
        exception = IOError
    else:
        exception = FileNotFoundError
    with pytest.raises(exception):
        upload_f = repo1.upload_file("nonexistent_file")


def test_upload_repo_absent_raises(tmpdir):
    controller = FakeController()

    controller.insert_repository(FileRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    somefile = tmpdir.join("some-file.txt")
    somefile.write(b"there is some binary data:\x00\x01\x02")

    repo_copy1 = client.get_repository("repo1").result()
    repo_copy2 = client.get_repository("repo1").result()

    # if repo's deleted
    assert repo_copy1.delete().result()

    exception = repo_copy2.upload_file(str(somefile)).exception()

    assert isinstance(exception, PulpException)
    assert "repo1 not found" in str(exception)
