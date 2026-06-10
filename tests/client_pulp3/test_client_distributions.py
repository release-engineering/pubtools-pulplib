"""
Test Pulp3Client distribution operations.
Generated-by: Claude Code
"""

import pytest
import httpx


@pytest.mark.anyio
async def test_create_distribution(respx_mock, pulp3_client):
    """Test creating a distribution."""
    respx_mock.post(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/distributions/rpm/rpm/"
    ).mock(
        return_value=httpx.Response(
            202,
            json={
                "task": "/pulp/api/v3/tasks/123/",
                "name": "test-dist",
                "base_path": "test/path",
            },
        )
    )

    async with pulp3_client() as client:
        task_href = await client.create_distribution(
            repository_href="/pulp/api/v3/repositories/rpm/rpm/456/",
            base_path="test/path",
            name="test-dist",
        )

        assert isinstance(task_href, str)
        assert task_href == "/pulp/api/v3/tasks/123/"


@pytest.mark.anyio
async def test_create_distribution_with_repository_href(respx_mock, pulp3_client):
    """Test creating a distribution with repository href."""
    respx_mock.post(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/distributions/rpm/rpm/"
    ).mock(
        return_value=httpx.Response(
            202,
            json={
                "task": "/pulp/api/v3/tasks/789/",
                "name": "prod-dist",
                "base_path": "production/repo",
                "repository": "/pulp/api/v3/repositories/rpm/rpm/999/",
            },
        )
    )

    async with pulp3_client() as client:
        task_href = await client.create_distribution(
            repository_href="/pulp/api/v3/repositories/rpm/rpm/999/",
            base_path="production/repo",
            name="prod-dist",
        )

        assert isinstance(task_href, str)
        assert task_href == "/pulp/api/v3/tasks/789/"
