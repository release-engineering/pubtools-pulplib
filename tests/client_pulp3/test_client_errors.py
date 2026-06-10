"""
Test Pulp3Client error handling.
Generated-by: Claude Code
"""

import pytest
import httpx


@pytest.mark.anyio
async def test_404_not_found(respx_mock, pulp3_client):
    """Test that 404 errors are handled gracefully."""
    respx_mock.get(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/nonexistent/"
    ).mock(return_value=httpx.Response(404, json={"detail": "Not found"}))

    async with pulp3_client() as client:
        # Based on current implementation, 404 returns None
        result = await client._request("GET", "/nonexistent/")
        assert result is None


@pytest.mark.anyio
async def test_http_500_error_raises(respx_mock, pulp3_client):
    """Test that 500 errors raise HTTPStatusError."""
    respx_mock.get("https://pulp.example.com/api/pulp/test-domain/api/v3/status/").mock(
        return_value=httpx.Response(500, json={"detail": "Internal server error"})
    )

    async with pulp3_client() as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_status()


@pytest.mark.anyio
async def test_http_503_service_unavailable(respx_mock, pulp3_client):
    """Test that 503 errors raise HTTPStatusError."""
    respx_mock.get("https://pulp.example.com/api/pulp/test-domain/api/v3/status/").mock(
        return_value=httpx.Response(503, json={"detail": "Service unavailable"})
    )

    async with pulp3_client() as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_status()


@pytest.mark.anyio
async def test_json_decode_error_raises(respx_mock, pulp3_client):
    """Test that JSON decode errors raise JSONDecodeError."""
    respx_mock.get("https://pulp.example.com/api/pulp/test-domain/api/v3/status/").mock(
        return_value=httpx.Response(200, text="not json")
    )

    async with pulp3_client() as client:
        from json import JSONDecodeError

        with pytest.raises(JSONDecodeError):
            await client.get_status()


@pytest.mark.anyio
async def test_connection_error(respx_mock, pulp3_client):
    """Test that connection errors are raised."""
    respx_mock.get("https://pulp.example.com/api/pulp/test-domain/api/v3/status/").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    async with pulp3_client() as client:
        with pytest.raises(httpx.ConnectError):
            await client.get_status()


@pytest.mark.anyio
async def test_404_after_retries(respx_mock, pulp3_client):
    """Test that 404 is handled correctly even with retries."""
    route = respx_mock.get(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/nonexistent/"
    )

    # First attempt fails with 500, second returns 404
    route.mock(
        side_effect=[
            httpx.Response(500, json={"detail": "Server error"}),
            httpx.Response(404, json={"detail": "Not found"}),
        ]
    )

    async with pulp3_client(max_retries=2) as client:
        result = await client._request("GET", "/nonexistent/")
        assert result is None
        # Should have tried twice (500 triggers retry, then 404)
        assert route.call_count == 2


@pytest.mark.anyio
async def test_http_401_unauthorized_raises(respx_mock, pulp3_client):
    """Test that 401 Unauthorized raises HTTPStatusError."""
    respx_mock.get("https://pulp.example.com/api/pulp/test-domain/api/v3/status/").mock(
        return_value=httpx.Response(401, json={"detail": "Unauthorized"})
    )

    async with pulp3_client() as client:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await client.get_status()

        assert exc_info.value.response.status_code == 401
