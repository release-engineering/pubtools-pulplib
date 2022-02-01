import datetime
import pytest
import attr

from pubtools.pulplib import FakeController, FileUnit, FileRepository


def test_update_no_id():
    controller = FakeController()
    client = controller.client

    # Try to update something with no ID; it should fail immediately
    # (no future) as we can't even try to update without an ID.
    with pytest.raises(ValueError) as excinfo:
        client.update_content(
            FileUnit(
                path="x",
                size=0,
                sha256sum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            )
        )

    # It should tell us why
    assert "unit_id missing on call to update_content()" in str(excinfo.value)


def test_update_nonexistent():
    controller = FakeController()
    client = controller.client

    # Try to update something which doesn't exist.
    update_f = client.update_content(
        FileUnit(
            unit_id="this-unit-is-missing",
            path="x",
            size=0,
            sha256sum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )
    )

    # It should fail, async.
    assert "unit not found: this-unit-is-missing" in str(update_f.exception())


def test_can_update_content(tmpdir):
    controller = FakeController()

    controller.insert_repository(FileRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    somefile = tmpdir.join("some-file.txt")
    somefile.write(b"there is some binary data:\x00\x01\x02")

    upload_f = repo1.upload_file(
        str(somefile),
        description="My great file",
        version="1.0",
        cdn_path="/foo/bar.txt",
    )

    # The future should resolve successfully
    tasks = upload_f.result()

    # The task should be successful.
    assert tasks[0].succeeded

    # File should now be in repo.
    units_in_repo = list(repo1.search_content())
    assert len(units_in_repo) == 1
    unit = units_in_repo[0]

    # Sanity check we got the right thing.
    assert unit.path == "some-file.txt"

    # Now let's try updating fields.
    new_unit = attr.evolve(
        unit,
        size=1000,
        description="My greater file",
        display_order=10,
        cdn_published=datetime.datetime(2021, 12, 6, 11, 19, 0),
    )

    update_f = client.update_content(new_unit)

    # It should succeed.
    update_f.result()

    # Now get the unit again.
    units_in_repo = list(repo1.search_content())
    assert len(units_in_repo) == 1
    unit_after_update = units_in_repo[0]

    # The mutable fields on the unit after update should be as expected:
    assert unit_after_update.description == "My greater file"
    assert unit_after_update.cdn_published == datetime.datetime(2021, 12, 6, 11, 19, 0)
    assert unit_after_update.display_order == 10
    # This one didn't change since it wasn't evolved
    assert unit_after_update.cdn_path == "/foo/bar.txt"
    assert unit_after_update.version == "1.0"
    # This one didn't change (even though we tried) because it's not mutable
    assert unit_after_update.size == 29
