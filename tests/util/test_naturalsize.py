import pytest

from pubtools.pulplib._impl.util import naturalsize


@pytest.mark.parametrize(
    "input,output",
    [
        (1, "1 Byte"),
        ("10", "10 Bytes"),
        (1234, "1.2 kB"),
        (1234567, "1.2 MB"),
        (678909876543, "678.9 GB"),
        (1000000000000, "1.0 TB"),
        ("874365287928728746529431", "874365.3 EB"),
    ],
)
def test_naturalsize(input, output):
    """
    Format a number of bytes like a human-readable filesize.
    """
    assert naturalsize(input) == output
