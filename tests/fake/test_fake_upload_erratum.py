import sys
import os

import pytest

from pubtools.pulplib import FakeController, ErratumUnit, YumRepository


def test_can_upload_units():
    """repo.upload_erratum() succeeds with fake client and populates units."""

    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    to_upload = ErratumUnit(
        id="RHBA-1234:56",
        summary="test advisory",
        # Add some existing memberships in an attempt to screw it up...
        # (they should not affect the upload)
        repository_memberships=["repo2", "repo3"],
    )

    upload_f = repo1.upload_erratum(to_upload)

    # Upload should complete successfully.
    tasks = upload_f.result()

    # At least one task.
    assert tasks

    # Every task should have succeeded.
    for t in tasks:
        assert t.succeeded

    # If I now search for content in that repo, or content across all repos...
    units_in_repo = list(repo1.search_content())
    units_all = list(client.search_content())

    # They should be equal
    assert units_all == units_in_repo

    # And they should be this
    assert units_in_repo == [
        ErratumUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            id="RHBA-1234:56",
            summary="test advisory",
            repository_memberships=["repo1"],
        )
    ]


def test_upload_overwrite():
    """repo.upload_erratum() can overwrite fields of an existing advisory."""

    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))
    controller.insert_repository(YumRepository(id="repo2"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()
    repo2 = client.get_repository("repo2").result()

    to_upload1 = ErratumUnit(id="RHBA-1234:56", summary="test advisory", version="1")
    to_upload2 = ErratumUnit(
        id="RHBA-1234:56",
        summary="updated test advisory",
        description="I've altered the deal",
        version="2",
    )
    to_upload3 = ErratumUnit(id="RHBA-1234:57", summary="a different advisory")

    # Upload all three of the above advisories.
    # Uploads 1 and 2 are for the same advisory (though we use
    # different repos to see what happens).
    assert repo1.upload_erratum(to_upload1).result()
    assert repo2.upload_erratum(to_upload2).result()
    assert repo2.upload_erratum(to_upload3).result()

    # Now let's check the outcome in each repo (and entire system).
    units_repo1 = sorted(repo1.search_content(), key=repr)
    units_repo2 = sorted(repo2.search_content(), key=repr)
    units_all = sorted(client.search_content(), key=repr)

    # What we expect to see is that the three uploads resulted in only
    # two errata, with the fields on the first advisory set to the values
    # after the most recent upload of it, and the second advisory equal to
    # the single upload for that advisory. Also, the first advisory is
    # now present in two repos.

    assert units_repo1 == [
        ErratumUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            id="RHBA-1234:56",
            summary="updated test advisory",
            description="I've altered the deal",
            version="2",
            repository_memberships=["repo1", "repo2"],
        )
    ]
    assert units_repo2 == [
        ErratumUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            id="RHBA-1234:56",
            summary="updated test advisory",
            description="I've altered the deal",
            version="2",
            repository_memberships=["repo1", "repo2"],
        ),
        ErratumUnit(
            unit_id="e6f4590b-9a16-4106-cf6a-659eb4862b21",
            id="RHBA-1234:57",
            summary="a different advisory",
            repository_memberships=["repo2"],
        ),
    ]

    assert units_repo2 == units_all


def test_upload_overwrite_noop():
    """repo.upload_erratum() doesn't overwrite erratum unit if version is unmodified."""

    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))
    controller.insert_repository(YumRepository(id="repo2"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()
    repo2 = client.get_repository("repo2").result()

    to_upload1 = ErratumUnit(id="RHBA-1234:56", summary="test advisory", version="3")
    to_upload2 = ErratumUnit(
        id="RHBA-1234:56",
        summary="updated test advisory",
        description="changed it, but no effect due to same version",
        version="3",
    )

    # Upload the advisory to two different repos.
    assert repo1.upload_erratum(to_upload1).result()
    assert repo2.upload_erratum(to_upload2).result()

    # Now let's check the outcome in each repo (and entire system).
    units_repo1 = sorted(repo1.search_content(), key=repr)
    units_repo2 = sorted(repo2.search_content(), key=repr)
    units_all = sorted(client.search_content(), key=repr)

    # What we expect to see is that we only have one advisory (as only
    # a single id was used), that advisory is present in two repos, and
    # the advisory content is equal to the first upload because version
    # was not bumped for the second upload.

    assert units_repo1 == [
        ErratumUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            id="RHBA-1234:56",
            summary="test advisory",
            version="3",
            repository_memberships=["repo1", "repo2"],
        )
    ]
    assert units_repo2 == units_repo1
    assert units_all == units_repo1
