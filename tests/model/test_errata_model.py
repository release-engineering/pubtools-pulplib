import os

import pytest

from pubtools.pulplib import ErratumUnit

from pubtools.pulplib import InvalidDataException


def test_container_list_invalid(data_path):
    """Provide invalid structure object to container_list attribute."""

    with open(
        os.path.join(data_path, "sample-erratum-invalid-container-list1.json"), "rt"
    ) as f:
        erratum_data = f.read()

    with pytest.raises(InvalidDataException):
        ErratumUnit.from_data(erratum_data)
