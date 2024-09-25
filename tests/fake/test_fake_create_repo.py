from pubtools.pulplib import FakeController, Repository, Distributor


def test_create_repository():
    """Client.create_repository() with fake client adds new repositories to controller."""
    controller = FakeController()

    client = controller.client
    repo_1 = client.create_repository(
        Repository(
            id="repo1",
            distributors=[Distributor(id="dist1", type_id="yum_distributor")],
        )
    )
    repo_2 = client.create_repository(
        Repository(
            id="repo2",
            distributors=[Distributor(id="dist2", type_id="yum_distributor")],
        )
    )

    # adding already existing repository has no effect
    _ = client.create_repository(
        Repository(
            id="repo1",
            distributors=[Distributor(id="dist1", type_id="yum_distributor")],
        )
    )
    # The change should be reflected in the controller,
    # with two repositories present
    assert controller.repositories == [repo_1.result(), repo_2.result()]
