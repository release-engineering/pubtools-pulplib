import pytest

from pubtools.pulplib import (
    FakeController,
    Criteria,
    Matcher,
    RpmUnit,
    ModulemdUnit,
    YumRepository,
)


@pytest.fixture
def controller():
    return FakeController()


def test_copy_content_empty_repo(controller):
    """copy_content from empty repo succeeds and copies nothing"""
    src = YumRepository(id="empty-repo")
    dest = YumRepository(id="dest-repo")
    controller.insert_repository(src)
    controller.insert_repository(dest)

    client = controller.client

    # Repos are initially detached, re-fetch them via client
    src = client.get_repository(src.id).result()
    dest = client.get_repository(dest.id).result()

    # It should succeed
    copy_tasks = list(client.copy_content(src, dest))

    # It should have at least one task
    assert copy_tasks

    for t in copy_tasks:
        # Every task should have succeeded
        assert t.succeeded

        # No units should have been copied
        assert not t.units


def test_copy_content_all(controller):
    """copy_content with no criteria copies all units from a repo"""
    src = YumRepository(id="src-repo")
    dest = YumRepository(id="dest-repo")
    other = YumRepository(id="other-repo")
    controller.insert_repository(src)
    controller.insert_repository(dest)
    controller.insert_repository(other)

    # Set up that both 'src' and 'other' contain some units.
    # The units in 'other' are there to ensure that copying only
    # happens from the given source repo and not other repos unexpectedly.
    src_units = [
        ModulemdUnit(
            name="module1", stream="s1", version=1234, context="a1b2", arch="x86_64"
        ),
        RpmUnit(
            name="bash",
            version="4.0",
            release="1",
            arch="x86_64",
            # Note: the next two fields aren't part of the unit key on RPM units.
            # We put these here specifically to verify they'll be filtered out
            # on the copy response (as a real Pulp server does).
            filename="bash-4.0-1.x86_64.rpm",
            signing_key="a1b2c3",
        ),
    ]
    controller.insert_units(src, src_units)
    controller.insert_units(
        other,
        [
            RpmUnit(
                name="glibc",
                version="5.0",
                release="1",
                arch="x86_64",
                sourcerpm="glibc-5.0-1.el5_11.1.src.rpm",
            )
        ],
    )

    client = controller.client

    # Repos are initially detached, re-fetch them via client
    src = client.get_repository(src.id).result()
    dest = client.get_repository(dest.id).result()

    # It should succeed
    copy_tasks = list(client.copy_content(src, dest))

    # Gather all units apparently copied
    units = sum([t.units for t in copy_tasks], [])

    # It should copy just the units we expect, from src.
    assert sorted(units, key=repr) == [
        ModulemdUnit(
            name="module1", stream="s1", version=1234, context="a1b2", arch="x86_64"
        ),
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64", epoch="0"),
    ]

    # The copy should also impact subsequent content searches.
    dest_units = list(dest.search_content())
    assert src_units == sorted(dest_units, key=repr)


def test_copy_content_with_criteria(controller):
    """copy_content can filter copied units by field values"""

    src = YumRepository(id="src-repo")
    dest = YumRepository(id="dest-repo")
    controller.insert_repository(src)
    controller.insert_repository(dest)

    src_units = [
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64"),
        RpmUnit(name="bash", version="4.0", release="2", arch="x86_64"),
        RpmUnit(name="bash", version="4.1", release="3", arch="x86_64"),
        RpmUnit(name="glibc", version="5.0", release="1", arch="x86_64"),
    ]
    controller.insert_units(src, src_units)

    client = controller.client

    # Repos are initially detached, re-fetch them via client
    src = client.get_repository(src.id).result()
    dest = client.get_repository(dest.id).result()

    # This is what we want to copy...
    crit = Criteria.and_(
        Criteria.with_field("name", "bash"),
        Criteria.with_field("release", Matcher.in_(["1", "3"])),
    )

    # Copy should succeed
    copy_tasks = list(client.copy_content(src, dest, crit))

    # It should have copied only those units matching the criteria
    units = sum([t.units for t in copy_tasks], [])
    assert sorted(units, key=repr) == [
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64", epoch="0"),
        RpmUnit(name="bash", version="4.1", release="3", arch="x86_64", epoch="0"),
    ]

    # The copy should also impact subsequent content searches.
    dest_units = list(dest.search_content())
    assert sorted(dest_units, key=repr) == [
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64", epoch="0"),
        RpmUnit(name="bash", version="4.1", release="3", arch="x86_64", epoch="0"),
    ]
