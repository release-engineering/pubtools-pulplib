import datetime

import pytest

from pubtools.pulplib import FakeController, Repository, Criteria, Matcher


def test_can_search_id():
    """Can search for a repo by ID with fake client."""
    controller = FakeController()

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2")

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)

    client = controller.client
    crit = Criteria.with_id("repo1")
    found = client.search_repository(crit).result().data

    assert found == [repo1]


def test_can_search_ids():
    """Can search for a repo by list of IDs with fake client."""
    controller = FakeController()

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2")
    repo3 = Repository(id="repo3")

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)
    controller.insert_repository(repo3)

    client = controller.client
    crit = Criteria.with_id(["repo1", "repo3", "other-id"])
    found = client.search_repository(crit).result().data

    assert sorted(found) == [repo1, repo3]


def test_can_search_id_exists():
    """Can search for a repo using exists operator with fake client."""
    controller = FakeController()

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2")

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)

    client = controller.client
    crit = Criteria.with_field("id", Matcher.exists())
    found = client.search_repository(crit).result().data

    assert sorted(found) == [repo1, repo2]


def test_search_no_result():
    controller = FakeController()

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2")

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)

    client = controller.client
    crit = Criteria.with_field("notes.whatever", "foobar")
    found = client.search_repository(crit).result().data

    assert found == []


def test_search_or():
    controller = FakeController()

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2")
    repo3 = Repository(id="repo3")

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)
    controller.insert_repository(repo3)

    client = controller.client
    crit = Criteria.or_(
        Criteria.with_id("repo3"), Criteria.with_field("id", Matcher.equals("repo1"))
    )
    found = client.search_repository(crit).result().data

    assert sorted(found) == [repo1, repo3]


def test_search_created_exists():
    controller = FakeController()

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2", created=datetime.datetime.utcnow())
    repo3 = Repository(id="repo3", created=datetime.datetime.utcnow())

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)
    controller.insert_repository(repo3)

    client = controller.client
    crit = Criteria.with_field("notes.created", Matcher.exists())
    found = client.search_repository(crit).result().data

    assert sorted(found) == [repo2, repo3]


def test_search_and():
    controller = FakeController()

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2", created=datetime.datetime.utcnow())
    repo3 = Repository(id="repo3", created=datetime.datetime.utcnow())

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)
    controller.insert_repository(repo3)

    client = controller.client
    crit = Criteria.and_(
        Criteria.with_field("notes.created", Criteria.exists), Criteria.with_id("repo2")
    )
    found = client.search_repository(crit).result().data

    assert sorted(found) == [repo2]


def test_search_null_and():
    """Search with an empty AND gives an error."""
    controller = FakeController()

    repo1 = Repository(id="repo1")

    controller.insert_repository(repo1)

    client = controller.client
    crit = Criteria.and_()
    assert "Invalid AND in search query" in str(
        client.search_repository(crit).exception()
    )


def test_search_null_or():
    """Search with an empty OR gives an error."""
    controller = FakeController()

    repo1 = Repository(id="repo1")

    controller.insert_repository(repo1)

    client = controller.client
    crit = Criteria.or_()
    assert "Invalid OR in search query" in str(
        client.search_repository(crit).exception()
    )


def test_search_bad_criteria():
    """Search with criteria of wrong type gives an error."""
    controller = FakeController()

    repo1 = Repository(id="repo1")

    controller.insert_repository(repo1)

    client = controller.client

    with pytest.raises(Exception) as exc:
        client.search_repository("not a valid criteria")

    assert "Not a criteria" in str(exc.value)


def test_search_created_timestamp():
    controller = FakeController()

    when = datetime.datetime(2019, 6, 11, 14, 47, 0, tzinfo=None)
    when_str = "2019-06-11T14:47:00Z"

    repo1 = Repository(id="repo1")
    repo2 = Repository(id="repo2", created=when)
    repo3 = Repository(id="repo3", created=datetime.datetime.utcnow())

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)
    controller.insert_repository(repo3)

    client = controller.client
    crit = Criteria.with_field("notes.created", when_str)
    found = client.search_repository(crit).result().data

    assert sorted(found) == [repo2]


def test_search_mapped_field_eq():
    """Can do equality search with fields subject to Python<=>Pulp conversion."""
    controller = FakeController()

    repo1 = Repository(id="repo1", eng_product_id=888)
    repo2 = Repository(id="repo2", signing_keys=["foo", "bar"])
    repo3 = Repository(id="repo3", eng_product_id=123)

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)
    controller.insert_repository(repo3)

    client = controller.client
    keys_crit = Criteria.with_field("signing_keys", ["foo", "bar"])
    product_crit = Criteria.with_field("eng_product_id", 123)
    found_by_keys = client.search_repository(keys_crit).result().data
    found_by_product = client.search_repository(product_crit).result().data

    assert found_by_keys == [repo2]
    assert found_by_product == [repo3]


def test_search_mapped_field_in():
    """Can do 'in' search with fields subject to Python<=>Pulp conversion."""
    controller = FakeController()

    repo1 = Repository(id="repo1", eng_product_id=888)
    repo2 = Repository(id="repo2", eng_product_id=123)
    repo3 = Repository(id="repo3", eng_product_id=456)

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)
    controller.insert_repository(repo3)

    client = controller.client
    crit = Criteria.with_field("eng_product_id", Matcher.in_([123, 456]))
    found = client.search_repository(crit).result().data

    assert sorted(found) == [repo2, repo3]


def test_search_mapped_field_regex():
    """Can do regex search with fields subject to Python<=>Pulp conversion."""
    controller = FakeController()

    repo1 = Repository(id="repo1", type="foobar")
    repo2 = Repository(id="repo2", type="foobaz")
    repo3 = Repository(id="repo3", type="quux")

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)
    controller.insert_repository(repo3)

    client = controller.client
    crit = Criteria.with_field("type", Matcher.regex("fooba[rz]"))
    found = client.search_repository(crit).result().data

    assert sorted(found) == [repo1, repo2]


def test_search_created_regex():
    """Can search using regular expressions."""

    controller = FakeController()

    when1 = datetime.datetime(2019, 6, 11, 14, 47, 0, tzinfo=None)
    when2 = datetime.datetime(2019, 3, 1, 1, 1, 0, tzinfo=None)
    when3 = datetime.datetime(2019, 6, 1, 1, 1, 0, tzinfo=None)

    repo1 = Repository(id="repo1", created=when1)
    repo2 = Repository(id="repo2", created=when2)
    repo3 = Repository(id="repo3", created=when3)
    repo4 = Repository(id="repo4")

    controller.insert_repository(repo1)
    controller.insert_repository(repo2)
    controller.insert_repository(repo3)
    controller.insert_repository(repo4)

    client = controller.client
    crit = Criteria.with_field("notes.created", Matcher.regex("19-06"))
    found = list(client.search_repository(crit).result().as_iter())

    assert sorted(found) == [repo1, repo3]


def test_search_paginates():
    controller = FakeController()

    repos = []
    for i in range(0, 1000):
        repo = Repository(id="repo-%s" % i)
        repos.append(repo)
        controller.insert_repository(repo)

    client = controller.client
    crit = Criteria.true()

    page = client.search_repository(crit).result()
    found_repos = [repo for repo in page.as_iter()]

    page_count = 1
    while page.next:
        page_count += 1
        page = page.next.result()

    # There should have been several pages (it is not defined exactly
    # what page size the fake client uses, but it should be relatively
    # small to enforce that clients think about pagination)
    assert page_count >= 10

    # All repos should have been found
    assert sorted(found_repos) == sorted(repos)
