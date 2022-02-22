import pytest

from pubtools.pulplib import (
    FakeController,
    Criteria,
    Matcher,
    RpmUnit,
    ErratumUnit,
    ModulemdUnit,
    YumRepository,
    RpmDependency,
)


@pytest.fixture
def controller():
    return FakeController()


@pytest.fixture
def populated_repo(controller):
    units = [
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64"),
        RpmUnit(
            content_type_id="srpm", name="bash", version="4.0", release="1", arch="src"
        ),
        RpmUnit(
            name="glibc",
            version="5.0",
            release="1",
            arch="x86_64",
            sourcerpm="glibc-5.0-1.el5_11.1.src.rpm",
            provides=[RpmDependency(name="gcc")],
        ),
        ModulemdUnit(
            name="module1", stream="s1", version=1234, context="a1b2", arch="x86_64"
        ),
        ModulemdUnit(
            name="module2", stream="s2", version=1234, context="a1b2", arch="x86_64"
        ),
        ErratumUnit(id="RHBA-1234:56", summary="The best advisory"),
    ]

    repo = YumRepository(id="repo1")
    controller.insert_repository(repo)
    controller.insert_units(repo, units)

    return controller.client.get_repository(repo.id).result()


def test_search_content_empty_repo(controller):
    """search_content on empty repo gives no results"""
    repo = YumRepository(id="empty-repo")
    controller.insert_repository(repo)

    assert list(controller.client.get_repository("empty-repo").search_content()) == []


def test_search_content_missing_repo(controller, populated_repo):
    """search_content on nonexistent repo raises"""
    # Get an additional reference to the same repo
    repo = controller.client.get_repository("repo1")

    # Now delete the repo through one reference
    populated_repo.delete().result()

    # Searching through the other reference should now return a failed future
    # with reasonable error
    assert "Repository id=repo1 not found" in str(repo.search_content().exception())


def test_search_content_unsupported_operator(populated_repo):
    """search_content using unsupported operators on content_type_id raises"""
    with pytest.raises(ValueError) as e:
        populated_repo.search_content(
            Criteria.with_field("content_type_id", Matcher.regex("foobar"))
        )

    assert "unsupported expression for content_type_id" in str(e.value)


def test_search_null_and(populated_repo):
    """Search with an empty AND gives an error."""
    crit = Criteria.and_()
    assert "Invalid AND in search query" in str(
        populated_repo.search_content(crit).exception()
    )


def test_search_content_default_crit(populated_repo):
    """search_content with default criteria on populated repo finds all units"""

    units = list(populated_repo.search_content())
    assert len(units) == 6


def test_search_content_by_type(populated_repo):
    """search_content for particular type returns matching content"""

    crit = Criteria.with_field("content_type_id", "rpm")
    units = list(populated_repo.search_content(crit))
    assert sorted(units) == [
        RpmUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            name="bash",
            version="4.0",
            release="1",
            arch="x86_64",
            repository_memberships=["repo1"],
        ),
        RpmUnit(
            unit_id="d4713d60-c8a7-0639-eb11-67b367a9c378",
            name="glibc",
            version="5.0",
            release="1",
            arch="x86_64",
            sourcerpm="glibc-5.0-1.el5_11.1.src.rpm",
            repository_memberships=["repo1"],
            provides=[RpmDependency(name="gcc")],
        ),
    ]


def test_search_erratum_by_type(populated_repo):
    """search_content for erratum returns matching content"""

    crit = Criteria.with_field("content_type_id", "erratum")
    units = list(populated_repo.search_content(crit))
    assert units == [
        ErratumUnit(
            unit_id="85776e9a-dd84-f39e-7154-5a137a1d5006",
            id="RHBA-1234:56",
            summary="The best advisory",
            repository_memberships=["repo1"],
        )
    ]


def test_search_content_by_unit_field(populated_repo):
    """search_content on regular field returns matching content"""

    crit = Criteria.with_field("name", "bash")
    units = list(populated_repo.search_content(crit))
    assert sorted(units) == [
        RpmUnit(
            unit_id="82e2e662-f728-b4fa-4248-5e3a0a5d2f34",
            content_type_id="srpm",
            name="bash",
            version="4.0",
            release="1",
            arch="src",
            repository_memberships=["repo1"],
        ),
        RpmUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            name="bash",
            version="4.0",
            release="1",
            arch="x86_64",
            repository_memberships=["repo1"],
        ),
    ]


def test_search_content_by_unit_type(populated_repo):
    """search_content on unit_type returns only units of that type"""

    crit = Criteria.with_unit_type(ModulemdUnit)
    units = list(populated_repo.search_content(crit))
    assert sorted(units) == [
        ModulemdUnit(
            unit_id="23a7711a-8133-2876-37eb-dcd9e87a1613",
            name="module1",
            stream="s1",
            version=1234,
            context="a1b2",
            arch="x86_64",
            repository_memberships=["repo1"],
        ),
        ModulemdUnit(
            unit_id="e6f4590b-9a16-4106-cf6a-659eb4862b21",
            name="module2",
            stream="s2",
            version=1234,
            context="a1b2",
            arch="x86_64",
            repository_memberships=["repo1"],
        ),
    ]


def test_search_content_mixed_fields(populated_repo):
    """search_content crossing multiple fields and types returns matching units"""

    crit = Criteria.and_(
        Criteria.with_field_in("content_type_id", ["rpm", "modulemd"]),
        Criteria.with_field_in("name", ["bash", "module1"]),
    )
    units = list(populated_repo.search_content(crit))

    # Note: sorting different types not natively supported, hence sorting by repr
    assert sorted(units, key=repr) == [
        ModulemdUnit(
            unit_id="23a7711a-8133-2876-37eb-dcd9e87a1613",
            name="module1",
            stream="s1",
            version=1234,
            context="a1b2",
            arch="x86_64",
            repository_memberships=["repo1"],
        ),
        RpmUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            name="bash",
            version="4.0",
            release="1",
            arch="x86_64",
            repository_memberships=["repo1"],
        ),
    ]


def test_search_content_subfields(populated_repo):
    """
    search_content using subfield in attributes that are lists of objects.
    This applies for 'provides' and 'requires' attributes in RpmUnit.
    """
    crit = Criteria.and_(
        Criteria.with_unit_type(RpmUnit), Criteria.with_field("provides.name", "gcc")
    )
    units = list(populated_repo.search_content(crit))

    assert units == [
        RpmUnit(
            unit_id="d4713d60-c8a7-0639-eb11-67b367a9c378",
            name="glibc",
            version="5.0",
            release="1",
            arch="x86_64",
            sourcerpm="glibc-5.0-1.el5_11.1.src.rpm",
            provides=[RpmDependency(name="gcc")],
            repository_memberships=["repo1"],
        )
    ]
