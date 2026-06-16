"""
Test Pulp3Client task polling functionality.
Generated-by: Claude Code
"""

import pytest
import httpx

from pubtools.pulplib._impl.client_pulp3.errors import Pulp3TaskException


@pytest.mark.anyio
async def test_poll_task_success(respx_mock, pulp3_client):
    """Test successful task polling with task ID."""
    task_id = "018d5c8e-6f42-7c6e-8e3b-7f8e3a8f7e3a"

    route = respx_mock.get(
        f"https://pulp.example.com/api/pulp/test-domain/api/v3/tasks/{task_id}/"
    )

    # First two polls show running, third shows completed
    route.mock(
        side_effect=[
            httpx.Response(
                200, json={"state": "running", "pulp_href": f"/tasks/{task_id}/"}
            ),
            httpx.Response(
                200, json={"state": "running", "pulp_href": f"/tasks/{task_id}/"}
            ),
            httpx.Response(
                200, json={"state": "completed", "pulp_href": f"/tasks/{task_id}/"}
            ),
        ]
    )

    async with pulp3_client() as client:
        result = await client.poll_task(task_id, poll_interval=0.01, timeout=5.0)

        assert isinstance(result, dict)
        assert result["state"] == "completed"
        assert route.call_count == 3


@pytest.mark.anyio
async def test_poll_task_with_href(respx_mock, pulp3_client):
    """Test task polling with task href (extracts ID from href)."""
    task_id = "018d5c8e-6f42-7c6e-8e3b-7f8e3a8f7e3a"
    task_href = f"/api/pulp/test-domain/api/v3/tasks/{task_id}/"

    route = respx_mock.get(
        f"https://pulp.example.com/api/pulp/test-domain/api/v3/tasks/{task_id}/"
    )

    route.mock(
        return_value=httpx.Response(
            200, json={"state": "completed", "pulp_href": task_href}
        )
    )

    async with pulp3_client() as client:
        # Pass full href, client should extract ID
        result = await client.poll_task(task_href, poll_interval=0.01, timeout=5.0)

        assert isinstance(result, dict)
        assert result["state"] == "completed"
        assert route.call_count == 1


@pytest.mark.anyio
async def test_poll_task_immediate_completion(respx_mock, pulp3_client):
    """Test task polling when task is already completed."""
    task_id = "018d5c8e-6f42-7c6e-8e3b-7f8e3a8f7e3a"

    route = respx_mock.get(
        f"https://pulp.example.com/api/pulp/test-domain/api/v3/tasks/{task_id}/"
    )

    route.mock(
        return_value=httpx.Response(
            200, json={"state": "completed", "pulp_href": f"/tasks/{task_id}/"}
        )
    )

    async with pulp3_client() as client:
        result = await client.poll_task(task_id, poll_interval=0.01, timeout=5.0)

        assert isinstance(result, dict)
        assert result["state"] == "completed"
        assert route.call_count == 1


@pytest.mark.anyio
async def test_poll_task_failure(respx_mock, pulp3_client):
    """Test task polling when task fails."""
    task_href = "018d5c8e-6f42-7c6e-8e3b-7f8e3a8f7e3a"

    respx_mock.get(
        f"https://pulp.example.com/api/pulp/test-domain/api/v3/tasks/{task_href}/"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "state": "failed",
                "pulp_href": f"/tasks/{task_href}/",
                "error": {"description": "Task failed due to error"},
            },
        )
    )

    async with pulp3_client() as client:
        with pytest.raises(Pulp3TaskException, match="Task .* failed"):
            await client.poll_task(task_href, poll_interval=0.01, timeout=5.0)


@pytest.mark.anyio
async def test_poll_task_canceled(respx_mock, pulp3_client):
    """Test task polling when task is canceled."""
    task_href = "018d5c8e-6f42-7c6e-8e3b-7f8e3a8f7e3a"

    respx_mock.get(
        f"https://pulp.example.com/api/pulp/test-domain/api/v3/tasks/{task_href}/"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "state": "canceled",
                "pulp_href": f"/tasks/{task_href}/",
                "error": {"description": "Task was canceled"},
            },
        )
    )

    async with pulp3_client() as client:
        with pytest.raises(Pulp3TaskException, match="Task .* canceled"):
            await client.poll_task(task_href, poll_interval=0.01, timeout=5.0)


@pytest.mark.anyio
async def test_poll_task_timeout(respx_mock, pulp3_client):
    """Test task polling timeout."""
    task_href = "018d5c8e-6f42-7c6e-8e3b-7f8e3a8f7e3a"

    # Task never completes, always returns running
    respx_mock.get(
        f"https://pulp.example.com/api/pulp/test-domain/api/v3/tasks/{task_href}/"
    ).mock(
        return_value=httpx.Response(
            200, json={"state": "running", "pulp_href": f"/tasks/{task_href}/"}
        )
    )

    async with pulp3_client() as client:
        with pytest.raises(TimeoutError):
            await client.poll_task(task_href, poll_interval=0.01, timeout=0.1)
