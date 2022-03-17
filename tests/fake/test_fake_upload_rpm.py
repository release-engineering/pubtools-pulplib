import sys
import os

import pytest

from pubtools.pulplib import FakeController, RpmUnit, YumRepository, RpmDependency


@pytest.mark.parametrize("use_file_object", [False, True])
def test_can_upload_units(data_path, use_file_object):
    """repo.upload_rpm() succeeds with fake client and populates units."""

    rpm_path = os.path.join(data_path, "rpms/walrus-5.21-1.noarch.rpm")
    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    to_upload = rpm_path
    if use_file_object:
        to_upload = open(rpm_path, "rb")

    upload_f = repo1.upload_rpm(to_upload)

    # Upload should complete successfully.
    tasks = upload_f.result()

    # At least one task.
    assert tasks

    # Every task should have succeeded.
    for t in tasks:
        assert t.succeeded

    # If I now search for content in that repo, or content across all repos...
    units_in_repo = sorted(repo1.search_content().result(), key=lambda u: u.sha256sum)
    units_all = sorted(client.search_content().result(), key=lambda u: u.sha256sum)

    # They should be equal
    assert units_all == units_in_repo

    # And they should be this
    assert units_in_repo == [
        RpmUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            name="walrus",
            version="5.21",
            release="1",
            arch="noarch",
            epoch="0",
            signing_key="f78fb195",
            filename="walrus-5.21-1.noarch.rpm",
            sourcerpm="walrus-5.21-1.src.rpm",
            md5sum="6a3eec6d45e0ea80eab05870bf7a8d4b",
            sha1sum="8dea2b64fc52062d79d5f96ba6415bffae4d2153",
            sha256sum="e837a635cc99f967a70f34b268baa52e0f412c1502e08e924ff5b09f1f9573f2",
            content_type_id="rpm",
            repository_memberships=["repo1"],
            requires=[
                RpmDependency(
                    name="rpmlib(CompressedFileNames)",
                    version="3.0.4",
                    release="1",
                    flags="LE",
                    epoch="0",
                ),
                RpmDependency(
                    name="rpmlib(PayloadFilesHavePrefix)",
                    version="4.0",
                    release="1",
                    flags="LE",
                    epoch="0",
                ),
            ],
            provides=[
                RpmDependency(
                    name="walrus", version="5.21", release="1", flags="EQ", epoch="0"
                )
            ],
        )
    ]


def test_can_upload_with_versionless_deps(data_path):
    """repo.upload_rpm() succeeds on RPM having versionless deps."""

    rpm_path = os.path.join(data_path, "rpms/crash-trace-command-1.0-4.el6.src.rpm")
    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    upload_f = repo1.upload_rpm(rpm_path)

    # Upload should complete successfully.
    tasks = upload_f.result()

    # At least one task.
    assert tasks

    # Every task should have succeeded.
    for t in tasks:
        assert t.succeeded

    # If I now search for content in that repo, or content across all repos...
    units_in_repo = sorted(repo1.search_content().result(), key=lambda u: u.sha256sum)
    units_all = sorted(client.search_content().result(), key=lambda u: u.sha256sum)

    # They should be equal
    assert units_all == units_in_repo

    # And they should be this
    assert units_in_repo == [
        RpmUnit(
            name="crash-trace-command",
            version="1.0",
            release="4.el6",
            arch="src",
            signing_key="fd431d51",
            filename="crash-trace-command-1.0-4.el6.src.rpm",
            md5sum="e06137db87b9b690fc36e8bac9071771",
            sha1sum="bacbb2ee0572d39b1ac8543cfe57c3e584ed986a",
            sha256sum="633e316eb23603ffc9474f926fcff152b2a61487653be97602fae06fcb46814d",
            repository_memberships=["repo1"],
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            requires=[
                RpmDependency(name="crash-devel"),
                RpmDependency(name="zlib-devel"),
                RpmDependency(
                    name="rpmlib(FileDigests)",
                    version="4.6.0",
                    release="1",
                    epoch="0",
                    flags="LE",
                ),
                RpmDependency(
                    name="rpmlib(CompressedFileNames)",
                    version="3.0.4",
                    release="1",
                    epoch="0",
                    flags="LE",
                ),
            ],
            provides=[],
        )
    ]
