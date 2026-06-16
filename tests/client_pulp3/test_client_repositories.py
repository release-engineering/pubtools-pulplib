"""
Test Pulp3Client repository operations.
Generated-by: Claude Code
"""

import pytest
import httpx


@pytest.mark.anyio
async def test_create_repository_success(respx_mock, pulp3_client):
    """Test successful repository creation."""
    respx_mock.post(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/repositories/rpm/rpm/"
    ).mock(
        return_value=httpx.Response(
            201,
            json={
                "pulp_href": "/pulp/api/v3/repositories/rpm/rpm/123/",
                "name": "test-repo",
                "description": "Test repository",
            },
        )
    )

    async with pulp3_client() as client:
        repo = await client.create_repository(
            name="test-repo", description="Test repository"
        )

        assert repo["name"] == "test-repo"
        assert repo["description"] == "Test repository"
        assert repo["pulp_href"] == "/pulp/api/v3/repositories/rpm/rpm/123/"


@pytest.mark.anyio
async def test_create_repository_with_kwargs(respx_mock, pulp3_client):
    """Test repository creation with additional kwargs."""
    respx_mock.post(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/repositories/rpm/rpm/"
    ).mock(
        return_value=httpx.Response(
            201,
            json={
                "pulp_href": "/pulp/api/v3/repositories/rpm/rpm/456/",
                "name": "test-repo-2",
                "retain_repo_versions": 3,
            },
        )
    )

    async with pulp3_client() as client:
        repo = await client.create_repository(
            name="test-repo-2", retain_repo_versions=3
        )

        assert repo["name"] == "test-repo-2"
        assert repo["retain_repo_versions"] == 3


@pytest.mark.anyio
async def test_create_publication(respx_mock, pulp3_client):
    """Test creating a publication for a repository."""
    respx_mock.post(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/publications/rpm/rpm/"
    ).mock(
        return_value=httpx.Response(
            202,
            json={
                "task": "/pulp/api/v3/tasks/789/",
                "repository": "/pulp/api/v3/repositories/rpm/rpm/123/",
            },
        )
    )

    async with pulp3_client() as client:
        task_href = await client.create_publication(
            repository_href="/pulp/api/v3/repositories/rpm/rpm/123/"
        )

        assert isinstance(task_href, str)
        assert task_href == "/pulp/api/v3/tasks/789/"
