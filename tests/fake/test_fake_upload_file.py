import sys

import pytest

from pubtools.pulplib import FakeController, FileUnit, FileRepository, PulpException


def test_can_upload_units(tmpdir):
    """repo.upload_file() succeeds with fake client and populates units."""
    controller = FakeController()

    controller.insert_repository(FileRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    somefile = tmpdir.join("some-file.txt")
    somefile.write(b"there is some binary data:\x00\x01\x02")

    otherfile = tmpdir.join("another.txt")
    otherfile.write("ahoy there")

    upload1_f = repo1.upload_file(str(somefile))
    upload2_f = repo1.upload_file(str(otherfile), relative_url="another/path.txt")

    for f in [upload1_f, upload2_f]:
        # The future should resolve successfully
        tasks = f.result()

        # The task should be successful.
        assert tasks[0].succeeded

    # If I now search for content in that repo, or content across all repos...
    units_in_repo = sorted(repo1.search_content().result(), key=lambda u: u.sha256sum)
    units_all = sorted(client.search_content().result(), key=lambda u: u.sha256sum)

    # They should be equal
    assert units_all == units_in_repo

    # And they should be this
    assert units_in_repo == [
        FileUnit(
            path="another/path.txt",
            size=10,
            sha256sum="94c0c9d847ecaa45df01999676db772e5cb69cc54e1ff9db31d02385c56a86e1",
            repository_memberships=["repo1"],
        ),
        FileUnit(
            path="some-file.txt",
            size=29,
            sha256sum="fad3fc1e6d583b2003ec0a5273702ed8fcc2504271c87c40d9176467ebe218cb",
            repository_memberships=["repo1"],
        ),
    ]


def test_can_upload_history(tmpdir):
    """repo.upload_file() succeeds with fake client and populates upload_history.

    Note that upload_history is deprecated, but remains working for now.
    """
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
    repo1 = client.get_repository("repo1")

    # If file's not found, Python 2 raises IOError and Python 3 raises
    # FileNotFoundError. The latter one is not defined in Python 2.
    if sys.version_info < (3,):
        exception = IOError
    else:
        exception = FileNotFoundError
    with pytest.raises(exception):
        upload_f = repo1.upload_file("nonexistent_file").result()


def test_upload_repo_absent_raises(tmpdir):
    controller = FakeController()

    controller.insert_repository(FileRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1")

    somefile = tmpdir.join("some-file.txt")
    somefile.write(b"there is some binary data:\x00\x01\x02")

    repo_copy1 = client.get_repository("repo1")
    repo_copy2 = client.get_repository("repo1")

    # if repo's deleted
    assert repo_copy1.delete().result()

    exception = repo_copy2.upload_file(str(somefile)).exception()

    assert isinstance(exception, PulpException)
    assert "repo1 not found" in str(exception)
