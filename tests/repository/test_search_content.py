import pytest
from pubtools.pulplib import (
    Repository,
    FileUnit,
    RpmUnit,
    ModulemdUnit,
    ModulemdDefaultsUnit,
    DetachedException,
    InvalidContentTypeException,
)

FAKE_UNIT_SEARCH = [
    {
        "metadata": {
            "_content_type_id": "iso",
            "name": "hello.txt",
            "size": 23,
            "checksum": "a" * 64,
        }
    },
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
    },
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
    },
    {
        "metadata": {
            "_content_type_id": "modulemd",
            "name": "md",
            "stream": "s1",
            "version": 1234,
            "context": "a1b2c3",
            "arch": "s390x",
        }
    },
    {
        "metadata": {
            "_content_type_id": "modulemd_defaults",
            "name": "mdd",
            "stream": "1.0",
            "repo_id": "some-repo",
            "profiles": {"p1": ["something"]},
        }
    },
]


def test_detached():
    """content searches raise if called on a detached repository object"""
    with pytest.raises(DetachedException):
        assert not Repository(id="some-repo").iso_content


def test_search_content_without_content_type(client, requests_mocker):
    """search_content raises if called without criteria containing _content_type_id"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=FAKE_UNIT_SEARCH,
    )

    with pytest.raises(InvalidContentTypeException):
        assert not repo._search_content()


def test_iso_content(client, requests_mocker):
    """iso_content returns correct units from the repository"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=FAKE_UNIT_SEARCH,
    )

    assert len(repo.iso_content) == 1
    assert repo.iso_content[0].content_type_id == "iso"


def test_rpm_content(client, requests_mocker):
    """rpm_content returns correct units from the repository"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=FAKE_UNIT_SEARCH,
    )

    assert len(repo.rpm_content) == 1
    assert repo.rpm_content[0].content_type_id == "rpm"


def test_srpm_content(client, requests_mocker):
    """srpm_content returns correct units from the repository"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=FAKE_UNIT_SEARCH,
    )

    assert len(repo.srpm_content) == 1
    assert repo.srpm_content[0].content_type_id == "srpm"


def test_modulemd_content(client, requests_mocker):
    """modulemd_content returns correct units from the repository"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=FAKE_UNIT_SEARCH,
    )

    assert len(repo.modulemd_content) == 1
    assert repo.modulemd_content[0].content_type_id == "modulemd"


def test_modulemd_defaults_content(client, requests_mocker):
    """modulemd_defaults_content returns correct units from the repository"""
    repo = Repository(id="some-repo")
    repo.__dict__["_client"] = client
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
        json=FAKE_UNIT_SEARCH,
    )

    assert len(repo.modulemd_defaults_content) == 1
    assert repo.modulemd_defaults_content[0].content_type_id == "modulemd_defaults"
