import pytest

from pubtools.pulplib import Repository, YumRepository, DetachedException


def test_from_data_gives_yum_repository():
    """Repository.from_data maps to YumRepository subclass when needed"""
    repo = Repository.from_data({"id": "my-repo", "notes": {"_repo-type": "rpm-repo"}})
    assert isinstance(repo, YumRepository)


def test_default_mutable_urls():
    """mutable_urls has expected default value"""
    assert YumRepository(id="foo").mutable_urls == ["repodata/repomd.xml"]


def test_can_hash():
    """a default YumRepository is hashable"""
    repo = YumRepository(id="foo")
    reposet = set()
    reposet.add(repo)
    assert repo in reposet


def test_from_data_relative_url():
    """relative_url is initialized from distributors when possible"""
    repo = Repository.from_data(
        {
            "id": "my-repo",
            "notes": {"_repo-type": "rpm-repo"},
            "distributors": [
                {
                    "id": "yum_distributor",
                    "distributor_type_id": "yum_distributor",
                    "config": {"relative_url": "some/publish/path"},
                }
            ],
        }
    )

    assert repo.relative_url == "some/publish/path"


def test_from_data_skip_rsync_repodata():
    """skip_rsync_repodata is initialized from distributors when possible"""
    repo = Repository.from_data(
        {
            "id": "my-repo",
            "notes": {"_repo-type": "rpm-repo"},
            "distributors": [
                {
                    "id": "cdn_distributor",
                    "distributor_type_id": "rpm_rsync_distributor",
                    "config": {"skip_repodata": True},
                }
            ],
        }
    )
    assert repo.skip_rsync_repodata


def test_populate_attrs():
    """test populate attributes are correctly parsed from repo notes"""
    repo = Repository.from_data(
        {
            "id": "my-repo",
            "notes": {
                "_repo-type": "rpm-repo",
                "content_set": "fake_content_set",
                "population_sources": ["populate_repo1", "populate_repo2"],
                "ubi_population": True,
                "ubi_config_version": "fake_ubi_config_version",
            },
            "distributors": [],
        }
    )
    assert repo.population_sources == ["populate_repo1", "populate_repo2"]
    assert repo.ubi_population
    assert repo.content_set == "fake_content_set"
    assert repo.ubi_config_version == "fake_ubi_config_version"


def test_productid_attrs():
    """All attributes relating to productid are correctly parsed from repo notes."""

    repo = Repository.from_data(
        {
            "id": "my-repo",
            "notes": {
                "_repo-type": "rpm-repo",
                "arch": "x86_64",
                "product_versions": '["1.4", "1.100", "1.2"]',
                "platform_full_version": "whatever",
                "eng_product": "123",
            },
            "distributors": [],
        }
    )

    assert repo.arch == "x86_64"
    assert repo.eng_product_id == 123
    assert repo.platform_full_version == "whatever"

    # Note the version-aware sorting: 1.100 is larger than 1.4
    assert repo.product_versions == ["1.2", "1.4", "1.100"]


def test_product_versions_unusual_attrs():
    """Odd values in product_versions are tolerated."""

    repo = Repository.from_data(
        {
            "id": "my-repo",
            "notes": {
                "_repo-type": "rpm-repo",
                "product_versions": '["1.4", 234, "1.100", "not numeric"]',
            },
            "distributors": [],
        }
    )

    assert repo.product_versions == ["1.100", "1.4", "234", "not numeric"]


def test_related_repositories(client, requests_mocker):
    """test Repository.get_*_repository returns expected objects"""

    repo_binary_test = YumRepository(id="repo_binary", relative_url="some/repo/os")
    repo_binary_test.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/distributors/search/",
        [
            {
                "json": [
                    {
                        "id": "yum_distributor",
                        "distributor_type_id": "yum_distributor",
                        "repo_id": "repo_debug",
                        "config": {"relative_url": "some/repo/debug"},
                    }
                ]
            },
            {
                "json": [
                    {
                        "id": "yum_distributor",
                        "distributor_type_id": "yum_distributor",
                        "repo_id": "repo_source",
                        "config": {"relative_url": "some/repo/SRPMS"},
                    }
                ]
            },
        ],
    )

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/search/",
        [{"json": [{"id": "repo_debug"}]}, {"json": [{"id": "repo_source"}]}],
    )

    # Request for binary repo should return identical object
    assert repo_binary_test is repo_binary_test.get_binary_repository().result()
    assert repo_binary_test.get_binary_repository().id == "repo_binary"
    # Requests for debug and source repositories return correct repositories
    assert repo_binary_test.get_debug_repository().id == "repo_debug"
    assert repo_binary_test.get_source_repository().id == "repo_source"


def test_related_repositories_not_found(client, requests_mocker):
    """test Repository.get_*_repository returns Future[None] if repository is not found"""

    repo_binary_test = YumRepository(id="repo_binary", relative_url="some/repo/os")
    repo_binary_test.__dict__["_client"] = client

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/distributors/search/", json=[]
    )

    repo = repo_binary_test.get_source_repository()
    assert repo.result() is None


def test_related_repositories_detached_client():
    repo_binary_test = YumRepository(id="repo_binary", relative_url="some/repo/os")
    repo_binary_test.__dict__["_client"] = None

    with pytest.raises(DetachedException):
        repo_binary_test.get_binary_repository()
