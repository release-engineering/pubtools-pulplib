import datetime
import pytest

from pubtools.pulplib import Repository, Distributor, InvalidDataException


def test_missing_props():
    """from_data raises if input data misses necessary data"""
    with pytest.raises(InvalidDataException):
        Repository.from_data({"missing": "necessary props"})


def test_bad_id():
    """from_data raises if input data has id of wrong type"""
    with pytest.raises(InvalidDataException):
        Repository.from_data({"id": ["foo", "bar", "baz"]})


def test_attr_id():
    """from_data sets id attribute appropriately"""
    repo = Repository.from_data({"id": "some-repo"})
    assert repo.id == "some-repo"


def test_default_created():
    """from_data results in None created by default"""
    repo = Repository.from_data({"id": "some-repo"})
    assert repo.created is None


def test_bad_created(caplog):
    """from_data logs and raises if input data has created of wrong type"""
    with pytest.raises(InvalidDataException):
        Repository.from_data({"id": "some-repo", "notes": {"created": "whoops"}})

    # It should have logged about the bad data. We don't verify details
    # of the failure message since it relies too heavily on implementation
    # details (e.g. stringification of class)
    assert "An error occurred while loading Pulp data!" in caplog.text


def test_is_temporary():
    """from_data is_temporary is True if expected note is present"""
    repo = Repository.from_data({"id": "some-repo", "notes": {"pub_temp_repo": True}})
    assert repo.is_temporary


def test_is_not_temporary():
    """from_data is_temporary is False by default"""
    repo = Repository.from_data({"id": "some-repo"})
    assert not repo.is_temporary


def test_attr_created():
    """from_data sets created attribute appropriately"""
    repo = Repository.from_data(
        {"id": "some-repo", "notes": {"created": "2019-06-11T12:10:00Z"}}
    )

    expected = datetime.datetime(2019, 6, 11, 12, 10, 0, tzinfo=None)
    assert repo.created == expected


def test_distributors_created():
    """from_data sets distributors attribute appropriately"""
    repo = Repository.from_data(
        {
            "id": "some-repo",
            "distributors": [
                {"id": "dist1", "distributor_type_id": "type1"},
                {"id": "dist2", "distributor_type_id": "type1"},
            ],
        }
    )

    assert repo.distributors == [
        Distributor(id="dist1", type_id="type1"),
        Distributor(id="dist2", type_id="type1"),
    ]


def test_distributors_last_publish():
    """from_data sets distributor last publish attribute appropriately"""
    repo = Repository.from_data(
        {
            "id": "some-repo",
            "distributors": [
                {
                    "id": "dist1",
                    "distributor_type_id": "type1",
                    "last_publish": "2019-06-17T01:23:45Z",
                }
            ],
        }
    )

    assert repo.distributor("dist1").last_publish == datetime.datetime(
        2019, 6, 17, 1, 23, 45
    )


def test_distributors_last_publish_null():
    """from_data accepts a null last_publish"""
    repo = Repository.from_data(
        {
            "id": "some-repo",
            "distributors": [
                {"id": "dist1", "distributor_type_id": "type1", "last_publish": None}
            ],
        }
    )

    assert repo.distributor("dist1").last_publish is None


def test_invalid_distributor_repo_id():
    """distributor's repo id being different from repo it's attached is invalid"""

    dist = Distributor(id="dist", type_id="yum_distributor", repo_id="repo")
    with pytest.raises(ValueError) as ex:
        repo = Repository(id="test_repo", distributors=[dist])

    assert "repo_id doesn't match for dist" in str(ex.value)
