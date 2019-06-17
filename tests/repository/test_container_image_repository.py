from pubtools.pulplib import Repository, ContainerImageRepository


def test_from_data_gives_container_image_repository():
    repo = Repository.from_data(
        {"id": "my-repo", "notes": {"_repo-type": "docker-repo"}}
    )
    assert isinstance(repo, ContainerImageRepository)


def test_default_registry_id():
    assert ContainerImageRepository(id="foo").registry_id == "foo"


def test_registry_id_from_distributor():
    repo = Repository.from_data(
        {
            "id": "my-repo",
            "notes": {"_repo-type": "docker-repo"},
            "distributors": [
                {
                    "id": "docker_web_distributor_name_cli",
                    "distributor_type_id": "docker_distributor_web",
                    "config": {"repo-registry-id": "some/repo"},
                }
            ],
        }
    )

    assert repo.registry_id == "some/repo"
