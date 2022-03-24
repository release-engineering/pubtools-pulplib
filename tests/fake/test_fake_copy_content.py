import pytest

from pubtools.pulplib import (
    FakeController,
    Criteria,
    Matcher,
    RpmUnit,
    ErratumUnit,
    ModulemdUnit,
    YumRepository,
    CopyOptions,
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
        ErratumUnit(id="RHSA-1111:22", summary="Fixes bad things"),
        ModulemdUnit(
            name="module1",
            stream="s1",
            version=1234,
            context="a1b2",
            arch="x86_64",
            repository_memberships=["repoA", "repoB"],
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
    # Note that these are incomplete views of the units, as (just like real pulp)
    # the fake will only return fields present in the unit_key after a copy.
    assert sorted(units, key=repr) == [
        ErratumUnit(id="RHSA-1111:22"),
        ModulemdUnit(
            name="module1", stream="s1", version=1234, context="a1b2", arch="x86_64"
        ),
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64", epoch="0"),
    ]

    # The copy should also impact subsequent content searches.
    dest_units = list(dest.search_content())

    # The units we get from the search are not *precisely* the same as src_units,
    # because repository_memberships has been updated.
    assert sorted(dest_units, key=repr) == [
        ErratumUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            id="RHSA-1111:22",
            summary="Fixes bad things",
            content_type_id="erratum",
            repository_memberships=["src-repo", "dest-repo"],
        ),
        ModulemdUnit(
            unit_id="82e2e662-f728-b4fa-4248-5e3a0a5d2f34",
            name="module1",
            stream="s1",
            version=1234,
            context="a1b2",
            arch="x86_64",
            content_type_id="modulemd",
            repository_memberships=["src-repo", "dest-repo", "repoA", "repoB"],
        ),
        RpmUnit(
            unit_id="d4713d60-c8a7-0639-eb11-67b367a9c378",
            name="bash",
            version="4.0",
            release="1",
            arch="x86_64",
            epoch="0",
            signing_key="a1b2c3",
            filename="bash-4.0-1.x86_64.rpm",
            content_type_id="rpm",
            repository_memberships=["src-repo", "dest-repo"],
        ),
    ]


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
    copy_tasks = list(
        client.copy_content(
            src, dest, crit, options=CopyOptions(require_signed_rpms=False)
        )
    )

    # It should have copied only those units matching the criteria
    units = sum([t.units for t in copy_tasks], [])
    assert sorted(units, key=repr) == [
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64", epoch="0"),
        RpmUnit(name="bash", version="4.1", release="3", arch="x86_64", epoch="0"),
    ]

    # The copy should also impact subsequent content searches.
    dest_units = list(dest.search_content())
    assert sorted(dest_units, key=repr) == [
        RpmUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            name="bash",
            version="4.0",
            release="1",
            arch="x86_64",
            epoch="0",
            repository_memberships=["src-repo", "dest-repo"],
        ),
        RpmUnit(
            unit_id="d4713d60-c8a7-0639-eb11-67b367a9c378",
            name="bash",
            version="4.1",
            release="3",
            arch="x86_64",
            epoch="0",
            repository_memberships=["src-repo", "dest-repo"],
        ),
    ]


def test_copy_requires_rpm_signature(controller):
    copy_sig = CopyOptions(require_signed_rpms=True)
    copy_nosig = CopyOptions(require_signed_rpms=False)

    src = YumRepository(id="src-repo")
    dest = YumRepository(id="dest-repo")
    controller.insert_repository(src)
    controller.insert_repository(dest)

    src_units = [
        # A signed RPM
        RpmUnit(
            name="bash",
            version="4.0",
            release="1",
            arch="x86_64",
            filename="bash-4.0-1.x86_64.rpm",
            signing_key="a1b2c3",
        ),
        # An unsigned RPM
        RpmUnit(
            name="ksh",
            version="5.0",
            release="1",
            arch="x86_64",
            filename="ksh-5.0-1.x86_64.rpm",
        ),
    ]
    controller.insert_units(src, src_units)

    client = controller.client

    # Repos are initially detached, re-fetch them via client
    src = client.get_repository(src.id).result()
    dest = client.get_repository(dest.id).result()

    # First, try a copy with default behavior.
    assert client.copy_content(src, dest).result()

    # It should have copied only the signed RPM into the dest repo.
    assert sorted([u.name for u in dest.search_content()]) == ["bash"]

    # Try again with the requires sig flag as true.
    assert client.copy_content(src, dest, options=copy_sig).result()

    # That shouldn't make any difference since the fake always uses
    # true as the default anyway.
    assert sorted([u.name for u in dest.search_content()]) == ["bash"]

    # Try again with the requires sig flag as false.
    assert client.copy_content(src, dest, options=copy_nosig).result()

    # This time we should finally see the unsigned RPM show up as well.
    assert sorted([u.name for u in dest.search_content()]) == ["bash", "ksh"]
