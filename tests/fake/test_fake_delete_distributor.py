from pubtools.pulplib import FakeController, Repository, Distributor


def test_can_delete():
    """distributor.delete() with fake client removes distributor from fake data."""
    controller = FakeController()

    repo1 = Repository(
        id="repo1",
        distributors=[
            Distributor(id="dist1", type_id="type1", repo_id="repo1"),
            Distributor(id="dist2", type_id="type2", repo_id="repo1"),
        ],
    )

    controller.insert_repository(repo1)

    client = controller.client
    repo1 = client.get_repository("repo1")

    # Call to delete should succeed
    delete_f = repo1.distributors[0].delete()

    # The future should resolve successfully
    tasks = delete_f.result()

    # It should have returned at least one successful task.
    assert tasks
    for task in tasks:
        assert task.succeeded

    # The change should be reflected in the controller, with the
    # deleted distributor no longer present
    assert controller.repositories == [
        Repository(
            id="repo1",
            distributors=[Distributor(id="dist2", type_id="type2", repo_id="repo1")],
        )
    ]


def test_delete_missing_repo_fails():
    """dist.delete() of distributor with absent repo fails."""
    controller = FakeController()

    controller.insert_repository(
        Repository(
            id="repo",
            distributors=[
                Distributor(id="somedist", type_id="sometype", repo_id="repo")
            ],
        )
    )

    client = controller.client

    # Get two handles to the repo, to set up the situation that
    # the distributor is not detached despite repo deletion
    repo1 = client.get_repository("repo")
    repo2 = client.get_repository("repo")
    dist = repo2.distributors[0]

    # We can delete the repo
    assert repo1.delete().result()

    # The distributor (obtained via repo2) is not detached, but nevertheless
    # deletion should fail as repo no longer exists
    assert "Repository id=repo not found" in str(dist.delete().exception())


def test_delete_missing_distributor_succeeds():
    """dist.delete() of absent distributor with fake client succeeds.

    Deleting a distributor succeeds with the fake client since it also succeeds
    with the real client.
    """
    controller = FakeController()

    controller.insert_repository(
        Repository(
            id="repo",
            distributors=[
                Distributor(id="somedist", type_id="sometype", repo_id="repo")
            ],
        )
    )

    client = controller.client

    # Get two handles to the repos/distributors so we can delete via one handle
    # and try to delete again via the other
    repo_copy1 = client.get_repository("repo")
    repo_copy2 = client.get_repository("repo")

    dist_copy1 = repo_copy1.distributors[0]
    dist_copy2 = repo_copy2.distributors[0]

    # First delete succeeds, with some tasks
    assert dist_copy1.delete().result()

    # Second delete also succeeds, but there are no tasks since distributor
    # already doesn't exist
    assert dist_copy2.delete().result() == []
