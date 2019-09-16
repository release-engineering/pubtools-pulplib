from pubtools.pulplib import FakeController, YumRepository, Distributor, PulpException


def test_can_publish():
    """repo.publish() succeeds with fake client and populates publish_history."""
    controller = FakeController()

    controller.insert_repository(
        YumRepository(
            id="repo1",
            distributors=[
                Distributor(id="yum_distributor", type_id="yum_distributor"),
                Distributor(id="cdn_distributor", type_id="rpm_rsync_distributor"),
            ],
        )
    )
    controller.insert_repository(YumRepository(id="repo2"))

    client = controller.client
    repo1 = client.get_repository("repo1")

    # Call to publish should succeed
    publish_f = repo1.publish()

    # The future should resolve successfully
    tasks = publish_f.result()

    # It should have returned at least one successful task.
    assert tasks
    for task in tasks:
        assert task.succeeded

    # The change should be reflected in the controller's publish history
    history = controller.publish_history

    assert len(history) == 1
    assert history[0].repository.id == "repo1"
    assert history[0].tasks == tasks


def test_publish_absent_raises():
    """repo.publish() of a nonexistent repo raises."""
    controller = FakeController()

    controller.insert_repository(
        YumRepository(
            id="repo1",
            distributors=[
                Distributor(id="yum_distributor", type_id="yum_distributor"),
                Distributor(id="cdn_distributor", type_id="rpm_rsync_distributor"),
            ],
        )
    )

    client = controller.client
    repo_copy1 = client.get_repository("repo1")
    repo_copy2 = client.get_repository("repo1")

    # If I delete the repo through one handle...
    assert repo_copy1.delete().result()

    # ...then publish through the other handle becomes impossible
    exception = repo_copy2.publish().exception()
    assert isinstance(exception, PulpException)
    assert "repo1 not found" in str(exception)
