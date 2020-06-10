import pytest

from pubtools.pulplib import Repository, ContainerImageRepository


def test_from_data_gives_container_image_repository():
    """Repository.from_data routes to ContainerImageRepository subclass when needed"""
    repo = Repository.from_data(
        {"id": "my-repo", "notes": {"_repo-type": "docker-repo"}}
    )
    assert isinstance(repo, ContainerImageRepository)


def test_default_registry_id():
    """registry_id defaults to repository ID"""
    assert ContainerImageRepository(id="foo").registry_id == "foo"


def test_registry_id_from_distributor():
    """registry_id is loaded from distributor when possible"""
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


@pytest.mark.parametrize(
    "config", [{}, {"repo-registry-id": ""}, {"repo-registry-id": None}]
)
def test_default_registry_id_from_distributor(config):
    """default registry_id is used when it's not set in distributor or set to null/empty string"""
    repo = Repository.from_data(
        {
            "id": "my-repo",
            "notes": {"_repo-type": "docker-repo"},
            "distributors": [
                {
                    "id": "docker_web_distributor_name_cli",
                    "distributor_type_id": "docker_distributor_web",
                    "config": config,
                }
            ],
        }
    )

    assert repo.registry_id == "my-repo"
