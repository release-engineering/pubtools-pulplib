from functools import partial

import attr
import pytest

from pubtools.pulplib import FakeController, Repository, PulpException, FileUnit


def test_can_construct():
    """A fake client can be constructed."""
    controller = FakeController()
    assert controller.client is not None


def test_can_get():
    """get_repository returns repository inserted via controller."""
    controller = FakeController()

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2")

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)

    client = controller.client
    found = client.get_repository("repo2").result()

    assert found == repo2


def test_get_missing_raises():
    """get_repository returns unsuccessful future if repo doesn't exist."""
    controller = FakeController()

    repo_f = controller.client.get_repository("some-repo")
    with pytest.raises(PulpException) as raised:
        repo_f.result()

    assert "some-repo not found" in str(raised.value)


def test_get_wrong_type_raises():
    """get_repository raises TypeError if passed argument of wrong type."""
    controller = FakeController()

    client = controller.client
    with pytest.raises(TypeError):
        client.get_repository(["oops", "should have been a string"])


def test_client_lifecycle():
    """FakeClient can be used in a with statement, and not afterwards."""
    controller = FakeController()

    with controller.client as client:
        # This should work OK
        assert client.search_repository().result()

    # But after end of 'with' statement, most public methods will no longer work
    for fn in [
        client.search_repository,
        client.search_content,
        client.search_distributor,
        partial(client.get_repository, "somerepo"),
        client.get_maintenance_report,
        partial(client.set_maintenance, {"what": "ever"}),
        client.get_content_type_ids,
    ]:
        with pytest.raises(RuntimeError) as excinfo:
            fn()

        assert "cannot schedule new futures after shutdown" in str(excinfo.value)


def test_can_insert_orphans():
    """insert_units with a null repo inserts units as orphans."""
    controller = FakeController()

    units = [
        FileUnit(
            path="bar",
            size=0,
            sha256sum="b1a6cb41223dcd02f208827517fe4b59a12684b76e15dbee645e9f9a9daa952e",
        ),
        FileUnit(
            path="quux",
            size=0,
            sha256sum="b1a6cb41223dcd02f208827517fe4b59a12684b76e15dbee645e9f9a9daa952e",
        ),
    ]

    # Can insert
    controller.insert_units(None, units)

    client = controller.client

    # If I now search for all content...
    found = list(client.search_content())

    for unit in found:
        # It should have an ID
        assert unit.unit_id
        # It should have memberships [] (no repos) rather than None (unknown repos)
        assert unit.repository_memberships == []

    # Other than those two fields, it should be identical to the input
    found_cmp = [
        attr.evolve(u, unit_id=None, repository_memberships=None) for u in found
    ]
    assert sorted(found_cmp, key=repr) == units
