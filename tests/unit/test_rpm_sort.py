from pubtools.pulplib import RpmUnit


def test_rpm_sort_epoch():
    """Tests vercmp sort with different epochs."""
    rpm_1 = RpmUnit(
        sha256sum="4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
        arch="ia64",
        epoch="1",
        name="glibc-headers",
        release="2.57.el4.1",
        repository_memberships=["fake-repository-id-3"],
        sourcerpm="glibc-2.3.4-2.57.el4.1.src.rpm",
        version="2.3.4",
    )

    rpm_2 = RpmUnit(
        sha256sum="4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
        arch="ia64",
        epoch="0",
        name="glibc-headers",
        release="2.57.el4.1",
        repository_memberships=["fake-repository-id-3"],
        sourcerpm="glibc-2.3.4-2.57.el4.1.src.rpm",
        version="2.3.4",
    )

    rpms = [rpm_1, rpm_2]

    sorted_rpms = sorted(rpms)

    assert sorted_rpms == [rpm_2, rpm_1]


def test_rpm_sort_release():
    """Tests vercmp sort with different releases."""

    rpm_1 = RpmUnit(
        sha256sum="4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
        arch="ia64",
        epoch="0",
        name="glibc-headers",
        release="2.57.el4.1",
        version="2.3.4",
    )

    rpm_2 = RpmUnit(
        sha256sum="4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
        arch="ia64",
        epoch="0",
        name="glibc-headers",
        release="2.56.el4.1",
        version="2.3.4",
    )

    rpms = [rpm_1, rpm_2]

    sorted_rpms = sorted(rpms)

    assert sorted_rpms == [rpm_2, rpm_1]


def test_rpm_sort_version():
    """Tests vercmp sort with different versions."""

    rpm_1 = RpmUnit(
        sha256sum="4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
        arch="ia64",
        epoch="0",
        name="glibc-headers",
        release="2.57.el4.1",
        version="2.3.5",
    )

    rpm_2 = RpmUnit(
        sha256sum="4f5a3a0da6f404f6d9988987cd75f13982bd655a0a4f692406611afbbc597679",
        arch="ia64",
        epoch="0",
        name="glibc-headers",
        release="2.57.el4.1",
        version="2.3.4",
    )

    rpms = [rpm_1, rpm_2]

    sorted_rpms = sorted(rpms)

    assert sorted_rpms == [rpm_2, rpm_1]
