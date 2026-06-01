"""
Test Pulp3Client HTTP request methods.
Generated-by: Claude Code
"""

import pytest
import httpx


@pytest.mark.anyio
async def test_get_status_success(respx_mock, pulp3_client):
    """Test successful status request."""
    respx_mock.get("https://pulp.example.com/api/pulp/test-domain/api/v3/status/").mock(
        return_value=httpx.Response(
            200,
            json={
                "versions": [{"component": "core", "version": "3.21.0"}],
                "online_workers": [],
            },
        )
    )

    async with pulp3_client() as client:
        status = await client.get_status()

        assert "versions" in status
        assert status["versions"][0]["component"] == "core"


@pytest.mark.anyio
async def test_request_with_204_no_content(respx_mock, pulp3_client):
    """Test that 204 No Content returns empty dict."""
    respx_mock.delete(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/distributions/rpm/rpm/123/"
    ).mock(return_value=httpx.Response(204))

    async with pulp3_client() as client:
        result = await client._request("DELETE", "/distributions/rpm/rpm/123/")
        assert result is None


@pytest.mark.anyio
async def test_search_content(respx_mock, pulp3_client):
    """Test content search."""
    query = "(sha256=abc123)"

    respx_mock.get(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/content/rpm/packages/"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 1,
                "results": [
                    {
                        "pulp_href": "/pulp/api/v3/content/rpm/packages/1/",
                        "name": "test-package",
                        "sha256": "abc123",
                    }
                ],
            },
        )
    )

    async with pulp3_client() as client:
        results = await client.search_content(query)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["name"] == "test-package"
        assert results[0]["sha256"] == "abc123"


@pytest.mark.anyio
async def test_search_content_with_fields(respx_mock, pulp3_client):
    """Test content search with specific fields."""
    query = "(sha256=def456)"

    respx_mock.get(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/content/rpm/packages/"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 1,
                "results": [
                    {
                        "pulp_href": "/pulp/api/v3/content/rpm/packages/2/",
                        "name": "another-package",
                    }
                ],
            },
        )
    )

    async with pulp3_client() as client:
        results = await client.search_content(query, fields=["name", "pulp_href"])

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["name"] == "another-package"


@pytest.mark.anyio
async def test_search_content_empty_results(respx_mock, pulp3_client):
    """Test content search with no results."""
    query = "(sha256=nonexistent)"

    respx_mock.get(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/content/rpm/packages/"
    ).mock(return_value=httpx.Response(200, json={"count": 0, "results": []}))

    async with pulp3_client() as client:
        results = await client.search_content(query)

        assert isinstance(results, list)
        assert len(results) == 0


@pytest.mark.anyio
async def test_search_content_handles_none_response(respx_mock, pulp3_client):
    """Test search_content when response is None (404)."""
    query = "(sha256=test)"

    respx_mock.get(
        "https://pulp.example.com/api/pulp/test-domain/api/v3/content/rpm/packages/"
    ).mock(return_value=httpx.Response(404, json={"detail": "Not found"}))

    async with pulp3_client() as client:
        results = await client.search_content(query)

        assert isinstance(results, list)
        assert len(results) == 0


@pytest.mark.anyio
async def test_build_query_sha256(pulp3_client):
    """Test building search query by SHA256 checksums."""
    async with pulp3_client() as client:
        checksums = ["abc123", "def456", "ghi789"]
        query = client.build_query_sha256(checksums)

        assert isinstance(query, str)
        assert "sha256=abc123" in query
        assert "sha256=def456" in query
        assert "sha256=ghi789" in query
        assert " OR " in query
        assert query.startswith("(")
        assert query.endswith(")")


@pytest.mark.anyio
async def test_build_query_sha256_single_checksum(pulp3_client):
    """Test building query with single checksum."""
    async with pulp3_client() as client:
        query = client.build_query_sha256(["single123"])

        assert isinstance(query, str)
        assert query == "(sha256=single123)"


@pytest.mark.anyio
async def test_successful_request_returns_dict(respx_mock, pulp3_client):
    """Test that successful requests return proper dict type."""
    respx_mock.get("https://pulp.example.com/api/pulp/test-domain/api/v3/status/").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    async with pulp3_client() as client:
        result = await client.get_status()

        assert isinstance(result, dict)
        assert result["status"] == "ok"


@pytest.mark.anyio
async def test_empty_json_response(respx_mock, pulp3_client):
    """Test that empty JSON object is handled correctly."""
    respx_mock.get("https://pulp.example.com/api/pulp/test-domain/api/v3/status/").mock(
        return_value=httpx.Response(200, json={})
    )

    async with pulp3_client() as client:
        result = await client.get_status()

        assert result == {}
        assert isinstance(result, dict)
