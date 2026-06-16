"""
Test Pulp3Client content operations.
Generated-by: Claude Code
"""

import pytest
import httpx


@pytest.mark.anyio
async def test_modify_repo_content_with_id(respx_mock, pulp3_client):
    """Test modifying repository content using repository ID."""
    repo_id = "123"

    respx_mock.post(
        f"https://pulp.example.com/api/pulp/test-domain/api/v3/repositories/rpm/rpm/{repo_id}/modify/"
    ).mock(return_value=httpx.Response(202, json={"task": "/pulp/api/v3/tasks/789/"}))

    async with pulp3_client() as client:
        task_href = await client.modify_repo_content(
            repository_href_or_id=repo_id,
            add_content_units=["content-1", "content-2"],
            remove_content_units=["content-3"],
        )

        assert isinstance(task_href, str)
        assert task_href == "/pulp/api/v3/tasks/789/"


@pytest.mark.anyio
async def test_modify_repo_content_with_href(respx_mock, pulp3_client):
    """Test modifying repository content using repository href."""
    repo_id = "456"
    repo_href = f"/api/pulp/test-domain/api/v3/repositories/rpm/rpm/{repo_id}/"

    respx_mock.post(
        f"https://pulp.example.com/api/pulp/test-domain/api/v3/repositories/rpm/rpm/{repo_id}/modify/"
    ).mock(return_value=httpx.Response(202, json={"task": "/pulp/api/v3/tasks/999/"}))

    async with pulp3_client() as client:
        task_href = await client.modify_repo_content(
            repository_href_or_id=repo_href,
            add_content_units=["content-1"],
        )

        assert isinstance(task_href, str)
        assert task_href == "/pulp/api/v3/tasks/999/"


@pytest.mark.anyio
async def test_modify_repo_content_add_only(respx_mock, pulp3_client):
    """Test adding content to repository."""
    repo_id = "456"

    respx_mock.post(
        f"https://pulp.example.com/api/pulp/test-domain/api/v3/repositories/rpm/rpm/{repo_id}/modify/"
    ).mock(return_value=httpx.Response(202, json={"task": "/pulp/api/v3/tasks/111/"}))

    async with pulp3_client() as client:
        task_href = await client.modify_repo_content(
            repository_href_or_id=repo_id,
            add_content_units=["content-1", "content-2"],
        )

        assert isinstance(task_href, str)
        assert task_href == "/pulp/api/v3/tasks/111/"


@pytest.mark.anyio
async def test_modify_repo_content_remove_only(respx_mock, pulp3_client):
    """Test removing content from repository."""
    repo_id = "789"

    respx_mock.post(
        f"https://pulp.example.com/api/pulp/test-domain/api/v3/repositories/rpm/rpm/{repo_id}/modify/"
    ).mock(return_value=httpx.Response(202, json={"task": "/pulp/api/v3/tasks/222/"}))

    async with pulp3_client() as client:
        task_href = await client.modify_repo_content(
            repository_href_or_id=repo_id,
            remove_content_units=["content-1"],
        )

        assert isinstance(task_href, str)
        assert task_href == "/pulp/api/v3/tasks/222/"


@pytest.mark.anyio
async def test_modify_repo_content_no_changes_raises(pulp3_client):
    """Test that modifying with no content raises ValueError."""
    async with pulp3_client() as client:
        with pytest.raises(ValueError, match="No content to modify"):
            await client.modify_repo_content(
                repository_href_or_id="123",
                add_content_units=None,
                remove_content_units=None,
            )
