"""
Basic Pulp3Client initialization and context manager tests.
Generated-by: Claude Code
"""

import pytest


@pytest.mark.anyio
async def test_client_initialization(pulp3_client):
    """Test that client can be initialized with basic parameters."""
    client = pulp3_client(auth=("user", "pass"), timeout=30.0)
    assert client._url == "https://pulp.example.com/api/pulp/test-domain/api/v3/"
    assert client._domain == "test-domain"
    assert client._api_path == "/api/pulp/test-domain/api/v3/"
    assert client._timeout == 30.0


@pytest.mark.anyio
async def test_client_initialization_custom_domain(pulp3_client):
    """Test that client can be initialized with a custom domain."""
    client = pulp3_client(domain="custom-domain")
    assert client._url == "https://pulp.example.com/api/pulp/custom-domain/api/v3/"
    assert client._domain == "custom-domain"
    assert client._api_path == "/api/pulp/custom-domain/api/v3/"


@pytest.mark.anyio
async def test_client_initialization_default_domain():
    """Test that client uses 'default' domain when not specified."""
    from pubtools.pulplib._impl.client_pulp3.client import Pulp3Client

    client = Pulp3Client(url="https://pulp.example.com")
    assert client._domain == "default"
    assert client._api_path == "/api/pulp/default/api/v3/"


@pytest.mark.anyio
async def test_client_initialization_with_retry_params(pulp3_client):
    """Test client initialization with custom retry parameters."""
    client = pulp3_client(max_retries=3, retry_min_wait=0.5, retry_max_wait=30.0)
    assert client._retry_policy is not None


@pytest.mark.anyio
async def test_client_context_manager(pulp3_client):
    """Test client can be used as async context manager."""
    async with pulp3_client() as client:
        assert client._client is not None
        assert client._limiter is not None

    # After exit, client should be closed
    assert client._client is None
    assert client._limiter is None


@pytest.mark.anyio
async def test_request_without_context_raises(pulp3_client):
    """Test that making requests outside context manager raises error."""
    client = pulp3_client()

    with pytest.raises(RuntimeError, match="not initialized"):
        await client.get_status()


@pytest.mark.anyio
async def test_client_with_auth(pulp3_client):
    """Test client initialization with authentication."""
    client = pulp3_client(auth=("username", "password"))
    assert client._auth is not None


@pytest.mark.anyio
async def test_client_with_cert(pulp3_client):
    """Test client initialization with certificate."""
    client = pulp3_client(cert="/path/to/cert.pem")
    assert client._cert == "/path/to/cert.pem"


@pytest.mark.anyio
async def test_client_verify_ssl(pulp3_client):
    """Test client initialization with SSL verification settings."""
    client = pulp3_client(verify=False)
    assert client._verify is False
