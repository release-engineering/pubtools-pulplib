import pytest

from pubtools.pulplib import FakeController, Repository, PulpException


def test_can_construct():
    controller = FakeController()
    assert controller.client is not None


def test_can_get():
    controller = FakeController()

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2")

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)

    client = controller.client
    found = client.get_repository("repo2").result()

    assert found == repo2


def test_get_missing_raises():
    controller = FakeController()

    repo_f = controller.client.get_repository("some-repo")
    with pytest.raises(PulpException) as raised:
        repo_f.result()

    assert "some-repo not found" in str(raised)


def test_get_wrong_type_raises():
    controller = FakeController()

    client = controller.client
    with pytest.raises(TypeError):
        client.get_repository(["oops", "should have been a string"])
