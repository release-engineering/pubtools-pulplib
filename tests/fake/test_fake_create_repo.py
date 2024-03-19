from pubtools.pulplib import FakeController, Repository


def test_create_repository():
    """Client.create_repository() with fake client adds new repositories to controller."""
    controller = FakeController()

    client = controller.client
    repo_1 = client.create_repository(Repository(id="repo1"))
    repo_2 = client.create_repository(Repository(id="repo2"))

    # adding already existing repository has no effect
    _ = client.create_repository(Repository(id="repo1"))
    # The change should be reflected in the controller,
    # with two repositories present
    assert controller.repositories == [repo_1.result(), repo_2.result()]
