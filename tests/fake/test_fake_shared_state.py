import pytest

from pubtools.pulplib import (
    FakeController,
    RpmUnit,
    YumRepository,
    CopyOptions,
)


@pytest.fixture
def controller():
    return FakeController()


def test_clients_share_state(controller):
    """Multiple clients created by the same controller share state"""
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

    client1 = controller.new_client()
    client2 = controller.new_client()

    # The two clients should not be the same object
    assert client1 is not client2

    # Repos are initially detached, re-fetch them via client
    src = client1.get_repository(src.id).result()
    dest = client1.get_repository(dest.id).result()

    # Do a copy via client1
    client1.copy_content(
        src, dest, options=CopyOptions(require_signed_rpms=False)
    ).result()

    # Then search for content via client2
    found_units = list(client2.search_content())

    # It should be able to see the outcome of the copy done via client1;
    # i.e. repository_memberships contains both repos after the copy
    assert sorted(found_units, key=repr) == [
        RpmUnit(
            name="bash",
            version="4.0",
            release="1",
            arch="x86_64",
            repository_memberships=["src-repo", "dest-repo"],
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
        ),
        RpmUnit(
            name="bash",
            version="4.0",
            release="2",
            arch="x86_64",
            repository_memberships=["src-repo", "dest-repo"],
            unit_id="82e2e662-f728-b4fa-4248-5e3a0a5d2f34",
        ),
        RpmUnit(
            name="bash",
            version="4.1",
            release="3",
            arch="x86_64",
            repository_memberships=["src-repo", "dest-repo"],
            unit_id="d4713d60-c8a7-0639-eb11-67b367a9c378",
        ),
        RpmUnit(
            name="glibc",
            version="5.0",
            release="1",
            arch="x86_64",
            repository_memberships=["src-repo", "dest-repo"],
            unit_id="23a7711a-8133-2876-37eb-dcd9e87a1613",
        ),
    ]
