from pubtools.pulplib import ModulemdUnit


def test_modulemd_artifacts_filenames():
    unit = ModulemdUnit(
        name="fake",
        stream="fake",
        version=1234,
        context="fake",
        arch="fake",
        artifacts=[
            "perl-utils-0:5.30.1-452.module+el8.4.0+8990+01326e37.noarch",
            "perl-version-7:0.99.24-441.module+el8.3.0+6718+7f269185.src",
            "perl-version-7:0.99.24-441.module+el8.3.0+6718+7f269185.x86_64",
        ],
    )

    filenames = unit.get_artifacts_filenames()
    # expected filenames should have the epoch stripped and added '.rpm' extension
    expected_filenames = [
        "perl-utils-5.30.1-452.module+el8.4.0+8990+01326e37.noarch.rpm",
        "perl-version-0.99.24-441.module+el8.3.0+6718+7f269185.src.rpm",
        "perl-version-0.99.24-441.module+el8.3.0+6718+7f269185.x86_64.rpm",
    ]
    assert sorted(filenames) == sorted(expected_filenames)


def test_modulemd_artifacts_filenames_without_srpm():
    unit = ModulemdUnit(
        name="fake",
        stream="fake",
        version=1234,
        context="fake",
        arch="fake",
        artifacts=[
            "perl-utils-0:5.30.1-452.module+el8.4.0+8990+01326e37.noarch",
            "perl-version-7:0.99.24-441.module+el8.3.0+6718+7f269185.src",
            "perl-version-7:0.99.24-441.module+el8.3.0+6718+7f269185.x86_64",
        ],
    )

    filenames = unit.get_artifacts_filenames(exclude_srpms=True)
    # expected filenames should have the epoch stripped and added '.rpm' extension
    # srpms are skipped
    expected_filenames = [
        "perl-utils-5.30.1-452.module+el8.4.0+8990+01326e37.noarch.rpm",
        "perl-version-0.99.24-441.module+el8.3.0+6718+7f269185.x86_64.rpm",
    ]
    assert sorted(filenames) == sorted(expected_filenames)
