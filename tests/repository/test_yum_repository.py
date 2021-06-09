from pubtools.pulplib import Repository, YumRepository


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
                "arch": "fake_arch",
                "population_sources": ["populate_repo1", "populate_repo2"],
                "ubi_population": True,
                "platform_full_version": "fake_full_version",
                "platform_major_version": "fake_major_version",
                "ubi_config_version": "fake_ubi_config_version",
            },
            "distributors": [],
        }
    )
    assert repo.population_sources == ["populate_repo1", "populate_repo2"]
    assert repo.ubi_population
    assert repo.content_set == "fake_content_set"
    assert repo.arch == "fake_arch"
    assert repo.platform_full_version == "fake_full_version"
    assert repo.platform_major_version == "fake_major_version"
    assert repo.ubi_config_version == "fake_ubi_config_version"
