from pubtools.pulplib import Repository, YumRepository


def test_from_data_gives_yum_repository():
    repo = Repository.from_data({"id": "my-repo", "notes": {"_repo-type": "rpm-repo"}})
    assert isinstance(repo, YumRepository)


def test_default_mutable_urls():
    assert YumRepository(id="foo").mutable_urls == ["repodata/repomd.xml"]


def test_from_data_relative_url():
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
