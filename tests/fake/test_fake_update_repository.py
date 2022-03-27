import datetime
import pytest
import attr

from pubtools.pulplib import FakeController, FileUnit, FileRepository


def test_update_missing_repo():
    controller = FakeController()
    client = controller.client

    # Try to update something which is previously unknown to the client.
    update_f = client.update_repository(FileRepository(id="whatever"))

    # It should fail telling us the repo doesn't exist
    assert "repository not found: whatever" in str(update_f.exception())


def test_can_update_repo():
    controller = FakeController()

    controller.insert_repository(
        FileRepository(id="repo", product_versions=["a", "b", "c"])
    )

    client = controller.client

    # Should be able to get the repo.
    repo = client.get_repository("repo").result()

    # Let's try putting it back. Note we try changing both some mutable
    # and immutable fields here.
    update_f = client.update_repository(
        attr.evolve(repo, eng_product_id=123, product_versions=["d", "b"])
    )

    # The update should succeed (and return None)
    assert update_f.result() is None

    # Try getting the same repo back.
    repo_updated = client.get_repository("repo").result()

    # It should be equal to this:
    assert repo_updated == FileRepository(
        id="repo",
        # product_versions is mutable, so it's what we asked for (with
        # values canonicalized by sorting)
        product_versions=["b", "d"],
        # eng_product_id is not mutable, so that update was ignored
        eng_product_id=None,
    )
