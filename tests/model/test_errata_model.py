import os
import json

import pytest

from pubtools.pulplib import ErratumUnit, Unit

from pubtools.pulplib import InvalidDataException


def test_container_list(data_path):
    """Test load of valid errata structure."""

    with open(os.path.join(data_path, "sample-erratum.json"), "rt") as f:
        erratum_data = json.loads(f.read())

    Unit.from_data(erratum_data)


def test_container_list_invalid(data_path):
    """Provide invalid structure object to container_list attribute."""

    with open(
        os.path.join(data_path, "sample-erratum-invalid-container-list1.json"), "rt"
    ) as f:
        erratum_data = json.loads(f.read())

    with pytest.raises(InvalidDataException):
        Unit.from_data(erratum_data)
