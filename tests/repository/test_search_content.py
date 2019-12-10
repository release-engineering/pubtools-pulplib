import pytest
from pubtools.pulplib import Repository, DetachedException


def test_detached():
    """content searches raise if called on a detached repository object"""
    with pytest.raises(DetachedException):
        assert not Repository(id="some-repo").iso_content


def test_iso_content(client, requests_mocker):
    """iso_content returns correct unit types"""
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

    isos = repo.iso_content

    assert len(isos) == 1
    assert isos[0].content_type_id == "iso"


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
                    "stream": "1.0",
                    "repo_id": "some-repo",
                    "profiles": {"p1": ["something"]},
                }
            }
        ],
    )

    modulemd_defaults = repo.modulemd_defaults_content

    assert len(modulemd_defaults) == 1
    assert modulemd_defaults[0].content_type_id == "modulemd_defaults"
