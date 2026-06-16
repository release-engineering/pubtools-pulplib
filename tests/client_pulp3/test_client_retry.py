"""
Test Pulp3Client retry behavior.
Generated-by: Claude Code
"""

import pytest
import httpx


@pytest.mark.anyio
async def test_retry_on_failure_then_success(respx_mock, pulp3_client):
    """Test that requests are retried on failure."""
    route = respx_mock.get(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/status/"
    )

    # First two attempts fail, third succeeds
    route.mock(
        side_effect=[
            httpx.Response(500, json={"detail": "Server error"}),
            httpx.Response(503, json={"detail": "Service unavailable"}),
            httpx.Response(200, json={"status": "ok"}),
        ]
    )

    async with pulp3_client(max_retries=3) as client:
        result = await client.get_status()
        assert result == {"status": "ok"}
        assert route.call_count == 3


@pytest.mark.anyio
async def test_retry_exhausted_raises(respx_mock, pulp3_client):
    """Test that exhausted retries raise exception."""
    route = respx_mock.get(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/status/"
    )

    # All attempts fail
    route.mock(return_value=httpx.Response(500, json={"detail": "Server error"}))

    async with pulp3_client(max_retries=2) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_status()

        # Should have tried max_retries times
        assert route.call_count == 2


@pytest.mark.anyio
async def test_retry_with_connection_error(respx_mock, pulp3_client):
    """Test retry behavior with connection errors."""
    route = respx_mock.get(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/status/"
    )

    # First attempt fails with connection error, second succeeds
    route.mock(
        side_effect=[
            httpx.ConnectError("Connection failed"),
            httpx.Response(200, json={"status": "ok"}),
        ]
    )

    async with pulp3_client(max_retries=3) as client:
        result = await client.get_status()
        assert result == {"status": "ok"}
        assert route.call_count == 2


@pytest.mark.anyio
async def test_no_retry_on_success(respx_mock, pulp3_client):
    """Test that successful requests are not retried."""
    route = respx_mock.get(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/status/"
    )

    route.mock(return_value=httpx.Response(200, json={"status": "ok"}))

    async with pulp3_client(max_retries=5) as client:
        result = await client.get_status()
        assert result == {"status": "ok"}
        # Should only call once on success
        assert route.call_count == 1
