from io import BytesIO
from xml.parsers import expat

import pytest

from pubtools.pulplib._impl.comps import units_for_xml


def test_can_parse_empty_root():
    """units_for_xml parses an empty <comps/> document OK."""

    for doc in (b"<comps/>", b"<comps></comps>"):
        buf = BytesIO(doc)

        # It should parse OK
        units = units_for_xml(buf)

        # It should be empty
        assert units == []


def test_empty_error():
    """units_for_xml raises on completely empty input."""

    buf = BytesIO(b"")

    with pytest.raises(expat.ExpatError):
        units_for_xml(buf)


def test_unclosed_error():
    """units_for_xml raises on document with unclosed tag."""

    buf = BytesIO(b"<comps><group></comps>")

    with pytest.raises(expat.ExpatError):
        units_for_xml(buf)
