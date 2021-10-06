import pytest

from pubtools.pulplib import (
    FakeController,
    Criteria,
    RpmUnit,
    ModulemdUnit,
    ModulemdDefaultsUnit,
    YumRepository,
    PulpException,
)


@pytest.fixture
def controller():
    return FakeController()


@pytest.fixture
def populated_units(controller):
    units1 = [
        RpmUnit(
            name="bash",
            version="4.0",
            release="1",
            arch="x86_64",
            repository_memberships=["repo1"],
        ),
        RpmUnit(
            content_type_id="srpm",
            name="bash",
            version="4.0",
            release="1",
            arch="src",
            repository_memberships=["repo1"],
        ),
        RpmUnit(
            name="glibc",
            version="5.0",
            release="1",
            arch="x86_64",
            repository_memberships=["repo1"],
        ),
        ModulemdUnit(
            name="module1",
            stream="s1",
            version=1234,
            context="a1b2",
            arch="x86_64",
            repository_memberships=["repo1"],
        ),
        ModulemdUnit(
            name="module2",
            stream="s2",
            version=1234,
            context="a1b2",
            arch="x86_64",
            repository_memberships=["repo1"],
        ),
        ModulemdDefaultsUnit(
            name="module1", repo_id="repo1", repository_memberships=["repo1"]
        ),
    ]
    units2 = [
        RpmUnit(
            name="glic",
            version="2.3.4",
            release="1",
            arch="x86_64",
            repository_memberships=["repo2"],
        ),
        RpmUnit(
            content_type_id="srpm",
            name="gnu-efi",
            version="3.0c",
            release="1",
            arch="src",
            repository_memberships=["repo2"],
        ),
    ]

    repo1 = YumRepository(id="repo1")
    repo2 = YumRepository(id="repo2")
    controller.insert_repository(repo1)
    controller.insert_units(repo1, units1)
    controller.insert_units(repo2, units2)


def test_search_content_all(populated_units, controller):
    """search_content_by_type with no criteria specified"""
    units1 = [
        u
        for u in controller.client.search_content(
            Criteria.with_field("content_type_id", "rpm")
        ).result()
    ]
    units2 = [
        u
        for u in controller.client.search_content(
            Criteria.with_field("content_type_id", "srpm")
        ).result()
    ]
    units3 = [u for u in controller.client.search_content().result()]
    assert len(units1) == 3
    assert len([u for u in units1 if u.content_type_id == "rpm"]) == 3
    assert len(units2) == 2
    assert len([u for u in units2 if u.content_type_id == "srpm"]) == 2
    # + two modulemd, one modulemd_defaults
    assert len(units3) == 8

    assert set(sum([u.repository_memberships for u in units1], [])) == set(
        ["repo1", "repo2"]
    )


def test_search_content_criteria(populated_units, controller):
    """search_content_by_type with criteria"""
    units1 = [
        u
        for u in controller.client.search_content(
            Criteria.with_field("name", "bash")
        ).result()
    ]
    # match both srpm and rpm
    assert len(units1) == 2
    assert sorted([u.arch for u in units1]) == ["src", "x86_64"]


def test_search_content_invalid_content_type(populated_units, controller):
    """search_content_by_type with invalid content type"""
    with pytest.raises(PulpException):
        for x in controller.client.search_content(
            Criteria.with_field("content_type_id", "invalid")
        ).result():
            pass


def test_search_content_all_pagination(populated_units, controller):
    """search_content_by_type with no criteria specified"""
    units1 = [
        u
        for u in controller.client.search_content(
            Criteria.with_field("content_type_id", "rpm")
        ).result()
    ]
    units2 = [
        u
        for u in controller.client.search_content(
            Criteria.with_field("content_type_id", "srpm")
        ).result()
    ]
    units3 = [u for u in controller.client.search_content().result()]
    assert len(units1) == 3
    assert len([u for u in units1 if u.content_type_id == "rpm"]) == 3
    assert len(units2) == 2
    assert len([u for u in units2 if u.content_type_id == "srpm"]) == 2
    # + two modulemd, one modulemd_defaults
    assert len(units3) == 8

    assert set(sum([u.repository_memberships for u in units1], [])) == set(
        ["repo1", "repo2"]
    )
