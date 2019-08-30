import pytest

from pubtools.pulplib import FileUnit


def test_negative_size():
    """Can't have a FileUnit with a size less than 0."""
    with pytest.raises(ValueError) as error:
        FileUnit(path="hello.txt", sha256sum="a" * 64, size=-30)
    assert "Not a valid size" in str(error.value)


def test_bad_sum():
    """Can't have a FileUnit with an invalid checksum string."""
    with pytest.raises(ValueError) as error:
        FileUnit(path="hello.txt", sha256sum="fake-sum", size=30)
    assert "Not a valid SHA256" in str(error.value)
