from pubtools.pulplib import FileUnit


def test_noninteger_size():
    """FileUnit.from_data accepts a floating point size."""

    loaded = FileUnit.from_data(
        {
            "_content_type_id": "iso",
            "name": "my-impossible-file",
            "checksum": "49ae93732fcf8d63fe1cce759664982dbd5b23161f007dba8561862adc96d063",
            "size": 123.4,
        }
    )

    assert loaded == FileUnit(
        path="my-impossible-file",
        size=123,
        sha256sum="49ae93732fcf8d63fe1cce759664982dbd5b23161f007dba8561862adc96d063",
        content_type_id="iso",
    )


def test_zero_size():
    """FileUnit.from_data accepts a size of zero."""

    loaded = FileUnit.from_data(
        {
            "_content_type_id": "iso",
            "name": "my-empty-file",
            "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "size": 0,
        }
    )

    assert loaded == FileUnit(
        path="my-empty-file",
        size=0,
        sha256sum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        content_type_id="iso",
    )
