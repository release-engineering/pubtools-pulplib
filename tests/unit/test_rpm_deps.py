from pubtools.pulplib import Unit


def test_rpm_requires_provides():
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
            "provides": [
                {
                    "name": "test-provides",
                    "version": "1.0",
                    "release": "1",
                    "epoch": "0",
                    "flags": "EQ",
                }
            ],
            "requires": [
                {
                    "name": "test-requires",
                    "version": "1.0",
                    "release": "1",
                    "epoch": "0",
                    "flags": "LT",
                }
            ],
        }
    )

    assert len(unit.provides) == 1
    provides_item = unit.provides[0]
    provides_item.name == "test-provides"
    provides_item.version == "1.0"
    provides_item.release == "1"
    provides_item.epoch == "0"
    provides_item.flags == "EQ"

    assert len(unit.requires) == 1
    requires_item = unit.requires[0]
    requires_item.name == "test-requires"
    requires_item.version == "1.0"
    requires_item.release == "1"
    requires_item.epoch == "0"
    requires_item.flags == "LT"
