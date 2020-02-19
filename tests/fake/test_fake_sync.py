from pubtools.pulplib import (
    FakeController,
    YumRepository,
    YumSyncOptions,
    PulpException,
)


def test_can_sync():
    """repo.sync() succeeds with fake client and populates sync_history."""
    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))
    controller.insert_repository(YumRepository(id="repo2"))

    client = controller.client
    repo1 = client.get_repository("repo1")

    # Call to sync should succeed
    sync_f = repo1.sync(YumSyncOptions(feed="mock://feed/"))

    # The future should resolve successfully
    tasks = sync_f.result()

    # It should have returned at least one successful task.
    assert tasks
    for task in tasks:
        assert task.succeeded

    # The change should be reflected in the controller's sync history
    history = controller.sync_history

    assert len(history) == 1
    assert history[0].repository.id == "repo1"
    assert history[0].tasks == tasks


def test_sync_absent_raises():
    """repo.sync() of a nonexistent repo raises."""
    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))

    client = controller.client
    repo_copy1 = client.get_repository("repo1")
    repo_copy2 = client.get_repository("repo1")

    # If I delete the repo through one handle...
    assert repo_copy1.delete().result()

    # ...then sync through the other handle becomes impossible
    exception = repo_copy2.sync(YumSyncOptions(feed="mock://feed/")).exception()
    assert isinstance(exception, PulpException)
    assert "repo1 not found" in str(exception)
