from pubtools.pulplib import Unit


def test_rpm_sums():
    """Checksum values come from expected fields on pulp unit."""

    unit = Unit.from_data(
        {
            "_content_type_id": "rpm",
            "name": "bash",
            "epoch": "0",
            "filename": "bash-x86_64.rpm",
            "version": "4.0",
            "release": "1",
            "arch": "x86_64",
            # Sums are stored in a dict per algorithm...
            "checksums": {
                "md5": "aaa07a382ec010c01889250fce66fb13",
                "sha1": "bbb9ae4aeea6946a8668445395ba10b7399523a0",
                "sha256": "ccce93732fcf8d63fe1cce759664982dbd5b23161f007dba8561862adc96d063",
            },
            # But there is also a top-level "checksum" which is always sha256.
            # Normally this should be exactly equal to checksums.sha256 of course;
            # in this test we force a difference so we can tell which value was used.
            "checksum": "ddde93732fcf8d63fe1cce759664982dbd5b23161f007dba8561862adc96d063",
        }
    )

    # It should get these two from the checksums dict.
    assert unit.md5sum == "aaa07a382ec010c01889250fce66fb13"
    assert unit.sha1sum == "bbb9ae4aeea6946a8668445395ba10b7399523a0"

    # This one should instead come from "checksum".
    assert (
        unit.sha256sum
        == "ddde93732fcf8d63fe1cce759664982dbd5b23161f007dba8561862adc96d063"
    )
