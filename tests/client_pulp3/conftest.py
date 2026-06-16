"""
Shared fixtures for Pulp3Client tests.
Generated-by: Claude Code
"""

import pytest
from pubtools.pulplib._impl.client_pulp3.client import Pulp3Client

# Default test configuration
TEST_PULP_URL = "https://pulp.example.com"
TEST_DOMAIN = "test-domain"
TEST_MAX_RETRIES = 1
TEST_RETRY_MIN_WAIT = 0.001
TEST_RETRY_MAX_WAIT = 0.01


@pytest.fixture(autouse=True)
def anyio_backend():
    """Configure anyio backend for all tests."""
    return "trio"


@pytest.fixture
def pulp3_client():
    """Factory fixture for creating Pulp3Client with test defaults.

    Returns a factory function that creates a client with fast retry settings.
    Can be called with custom parameters to override defaults.

    Usage:
        async with pulp3_client() as client:
            # use client

        async with pulp3_client(max_retries=5) as client:
            # use client with custom settings
    """

    def _create_client(
        url=TEST_PULP_URL,
        domain=TEST_DOMAIN,
        max_retries=TEST_MAX_RETRIES,
        retry_min_wait=TEST_RETRY_MIN_WAIT,
        retry_max_wait=TEST_RETRY_MAX_WAIT,
        **kwargs
    ):
        return Pulp3Client(
            url=url,
            domain=domain,
            max_retries=max_retries,
            retry_min_wait=retry_min_wait,
            retry_max_wait=retry_max_wait,
            **kwargs
        )

    return _create_client
