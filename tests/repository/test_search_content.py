import pytest
from pubtools.pulplib import Repository, DetachedException, Criteria, Matcher, FileUnit


def test_detached():
    """content searches raise if called on a detached repository object"""
    with pytest.raises(DetachedException):
        assert not Repository(id="some-repo").file_content


def test_complex_type_ids(client):
    """content searches raise if using criteria with unsupported operators on content_type_id"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client

    with pytest.raises(ValueError) as e:
        repo.search_content(
            Criteria.with_field("content_type_id", Matcher.regex("foobar"))
        )

    assert "unsupported expression for content_type_id" in str(e.value)


def test_mixed_search(client, requests_mocker):
    """Searching with a criteria mixing several fields works correctly"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=[
            {
                "metadata": {
                    "_content_type_id": "iso",
                    "name": "hello.txt",
                    "size": 23,
                    "checksum": "a" * 64,
                }
            }
        ],
    )

    crit = Criteria.and_(
        Criteria.with_field_in("content_type_id", ["rpm", "iso"]),
        Criteria.with_field("name", "hello.txt"),
    )

    files = list(repo.search_content(crit))

    assert files == [FileUnit(path="hello.txt", size=23, sha256sum="a" * 64)]

    history = requests_mocker.request_history

    # There should have been just one request
    assert len(history) == 1

    request = history[0]
    body = request.json()

    # This should have been the request body.
    assert body == {
        "criteria": {
            "type_ids": ["rpm", "iso"],
            "skip": 0,
            "limit": 2000,
            "filters": {"unit": {"name": {"$eq": "hello.txt"}}},
        }
    }


def test_search_content_type_id_in_or(client, requests_mocker):
    """Searching with a content_type_id within $or fails as unsupported"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client

    crit = Criteria.or_(
        Criteria.with_field("name", "hello.txt"),
        Criteria.with_field_in("content_type_id", ["rpm", "iso"]),
    )

    with pytest.raises(ValueError) as e:
        repo.search_content(crit).result()

    assert "Can't serialize criteria for Pulp query; too complicated" in str(e.value)


def test_file_content(client, requests_mocker):
    """file_content returns correct unit types"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=[
            {
                "metadata": {
                    "_content_type_id": "iso",
                    "name": "hello.txt",
                    "size": 23,
                    "checksum": "a" * 64,
                }
            }
        ],
    )

    files = repo.file_content

    assert len(files) == 1
    assert files[0].content_type_id == "iso"


def test_rpm_content(client, requests_mocker):
    """rpm_content returns correct unit types"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=[
            {
                "metadata": {
                    "_content_type_id": "rpm",
                    "name": "bash",
                    "epoch": "0",
                    "filename": "bash-x86_64.rpm",
                    "version": "4.0",
                    "release": "1",
                    "arch": "x86_64",
                }
            }
        ],
    )

    rpms = repo.rpm_content

    assert len(rpms) == 1
    assert rpms[0].content_type_id == "rpm"


def test_srpm_content(client, requests_mocker):
    """srpm_content returns correct unit types"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=[
            {
                "metadata": {
                    "_content_type_id": "srpm",
                    "name": "bash",
                    "epoch": "0",
                    "filename": "bash-x86_64.srpm",
                    "version": "4.0",
                    "release": "1",
                    "arch": "x86_64",
                }
            }
        ],
    )

    srpms = repo.srpm_content

    assert len(srpms) == 1
    assert srpms[0].content_type_id == "srpm"


def test_modulemd_content(client, requests_mocker):
    """modulemd_content returns correct unit types"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=[
            {
                "metadata": {
                    "_content_type_id": "modulemd",
                    "name": "md",
                    "stream": "s1",
                    "version": 1234,
                    "context": "a1b2c3",
                    "arch": "s390x",
                }
            }
        ],
    )

    modulemds = repo.modulemd_content

    assert len(modulemds) == 1
    assert modulemds[0].content_type_id == "modulemd"


def test_modulemd_defaults_content(client, requests_mocker):
    """modulemd_defaults_content returns correct unit types"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=[
            {
                "metadata": {
                    "_content_type_id": "modulemd_defaults",
                    "name": "mdd",
                    "repo_id": "some-repo",
                    "profiles": {"p1": ["something"]},
                }
            }
        ],
    )

    modulemd_defaults = repo.modulemd_defaults_content

    assert len(modulemd_defaults) == 1
    assert modulemd_defaults[0].content_type_id == "modulemd_defaults"
