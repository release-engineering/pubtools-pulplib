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
        ),
        ModulemdUnit(
            name="module1", stream="s1", version=1234, context="a1b2", arch="x86_64"
        ),
        ModulemdUnit(
            name="module2", stream="s2", version=1234, context="a1b2", arch="x86_64"
        ),
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
    assert len(units) == 5


def test_search_content_by_type(populated_repo):
    """search_content for particular type returns matching content"""

    crit = Criteria.with_field("content_type_id", "rpm")
    units = list(populated_repo.search_content(crit))
    assert sorted(units) == [
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64"),
        RpmUnit(
            name="glibc",
            version="5.0",
            release="1",
            arch="x86_64",
            sourcerpm="glibc-5.0-1.el5_11.1.src.rpm",
        ),
    ]


def test_search_content_by_unit_field(populated_repo):
    """search_content on regular field returns matching content"""

    crit = Criteria.with_field("name", "bash")
    units = list(populated_repo.search_content(crit))
    assert sorted(units) == [
        RpmUnit(
            content_type_id="srpm", name="bash", version="4.0", release="1", arch="src"
        ),
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64"),
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
            name="module1", stream="s1", version=1234, context="a1b2", arch="x86_64"
        ),
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64"),
    ]
