# Simple tests for the humanize.naturalsize fallback used in legacy envs.
#
# TODO: remove me when py2 support is dropped.

import pytest

from pubtools.pulplib._impl.client.humanize_compat import (
    fallback_naturalsize as naturalsize,
)


@pytest.mark.parametrize(
    "input,expected_output",
    [
        (0, "0.0 MB"),
        (23 * 1024 * 1024, "23.0 MB"),
        (23 * 1000 * 1000, "21.9 MB"),
        (13.5 * 1000 * 1024 * 1024, "13500.0 MB"),
    ],
)
def test_naturalsize(input, expected_output):
    assert naturalsize(input) == expected_output
