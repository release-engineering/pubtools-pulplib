"""
Tests for httpx log-level filtering in Pulp3Client.
"""

import logging

import pytest

# Import the module so the filter is installed.
import pubtools.pulplib._impl.client_pulp3.client  # noqa: F401


def test_httpx_info_reemitted_at_debug(caplog):
    """httpx INFO records must appear as DEBUG on pubtools.pulplib, not as INFO on httpx."""
    httpx_logger = logging.getLogger("httpx")

    # Set httpx to INFO directly (not via caplog.at_level) so the record reaches
    # our filter. Using nested caplog.at_level calls would overwrite the handler
    # level and silently drop the resulting pubtools.pulplib DEBUG record.
    orig_level = httpx_logger.level
    httpx_logger.setLevel(logging.INFO)
    try:
        with caplog.at_level(logging.DEBUG, logger="pubtools.pulplib"):
            httpx_logger.info(
                'HTTP Request: GET https://pulp.example.com/api/ "HTTP/1.1 200 OK"'
            )
    finally:
        httpx_logger.setLevel(orig_level)

    pubtools_debug = [
        r
        for r in caplog.records
        if r.name == "pubtools.pulplib" and r.levelno == logging.DEBUG
    ]
    assert any(
        "HTTP Request:" in r.message for r in pubtools_debug
    ), "Expected httpx INFO to be re-emitted at DEBUG on pubtools.pulplib"

    httpx_info = [
        r for r in caplog.records if r.name == "httpx" and r.levelno == logging.INFO
    ]
    assert (
        not httpx_info
    ), "httpx INFO records must not remain as INFO on the httpx logger"


def test_httpx_info_silent_at_info_level(caplog):
    """httpx INFO records must not appear at all when pubtools.pulplib is at INFO."""
    httpx_logger = logging.getLogger("httpx")

    with caplog.at_level(logging.INFO, logger="pubtools.pulplib"):
        httpx_logger.info(
            'HTTP Request: GET https://pulp.example.com/api/ "HTTP/1.1 200 OK"'
        )

    http_request_records = [r for r in caplog.records if "HTTP Request:" in r.message]
    assert (
        not http_request_records
    ), "httpx INFO records must not appear when pubtools.pulplib is at INFO level"


def test_httpx_debug_records_pass_through(caplog):
    """httpx DEBUG records (not INFO) must not be swallowed by the filter."""
    httpx_logger = logging.getLogger("httpx")

    with caplog.at_level(logging.DEBUG, logger="httpx"):
        httpx_logger.debug("some httpx debug message")

    httpx_debug = [
        r for r in caplog.records if r.name == "httpx" and r.levelno == logging.DEBUG
    ]
    assert any(
        "some httpx debug message" in r.message for r in httpx_debug
    ), "httpx DEBUG records must not be dropped by the filter"
