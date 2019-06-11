import pytest
import datetime

from pubtools.pulplib import FakeController, Repository, Criteria, PulpException


def test_can_delete():
    controller = FakeController()

    controller.insert_repository(Repository(id="repo1"))
    controller.insert_repository(Repository(id="repo2"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    # Call to delete should succeed
    delete_f = repo1.delete()

    # The future should resolve successfully
    tasks = delete_f.result()

    # It should have returned at least one successful task.
    assert tasks
    for task in tasks:
        assert task.succeeded

    # The change should be reflected in the controller, with the
    # deleted repo no longer present
    assert controller.repositories == [Repository(id="repo2")]


def test_delete_missing_repo_fails():
    controller = FakeController()

    controller.insert_repository(Repository(id="repo"))

    client = controller.client

    # We want to try deleting the same repo more than once.
    # We can't do this through a single reference since it would be detached
    # on delete, but if we get two handles to the same repo, we can.
    repo_copy1 = client.get_repository("repo").result()
    repo_copy2 = client.get_repository("repo").result()

    # First delete succeeds
    assert repo_copy1.delete().result()

    # Second delete should give an error since repo no longer exists
    exception = repo_copy2.delete().exception()
    assert isinstance(exception, PulpException)
    assert "Repository not found: repo" in str(exception)
