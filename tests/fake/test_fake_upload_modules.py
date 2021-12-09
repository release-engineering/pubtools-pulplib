import sys
import os

import pytest

from pubtools.pulplib import (
    FakeController,
    YumRepository,
    ModulemdUnit,
    ModulemdDefaultsUnit,
    ModulemdDependency,
)


@pytest.mark.parametrize("use_file_object", [False, True])
def test_can_upload_units(use_file_object, data_path):
    """repo.upload_modules() succeeds with fake client and populates units."""
    modules_path = os.path.join(data_path, "sample-modules.yaml")

    controller = FakeController()

    controller.insert_repository(YumRepository(id="repo1"))

    client = controller.client
    repo1 = client.get_repository("repo1").result()

    to_upload = modules_path
    if use_file_object:
        to_upload = open(to_upload, "rb")

    upload_f = repo1.upload_modules(to_upload)

    # Upload should complete successfully.
    tasks = upload_f.result()

    # At least one task.
    assert tasks

    # Every task should have succeeded.
    for t in tasks:
        assert t.succeeded

    # If I now search for content in that repo, or content across all repos...
    units_in_repo = sorted(repo1.search_content().result(), key=repr)
    units_all = sorted(client.search_content().result(), key=repr)

    # They should be equal
    assert units_all == units_in_repo

    # And they should be this
    assert units_in_repo == [
        ModulemdDefaultsUnit(
            unit_id="e3e70682-c209-4cac-629f-6fbed82c07cd",
            name="ant",
            repo_id="repo1",
            # Note, this tests that 1.10 does not get coerced to 1.1,
            # as happened in some tools previously.
            stream="1.10",
            profiles={"1.10": ["default"]},
            content_type_id="modulemd_defaults",
            repository_memberships=["repo1"],
        ),
        ModulemdDefaultsUnit(
            unit_id="d4713d60-c8a7-0639-eb11-67b367a9c378",
            name="dwm",
            repo_id="repo1",
            stream=None,
            profiles={
                "6.0": ["default"],
                "6.1": ["default"],
                "6.2": ["default"],
                "latest": ["default"],
            },
            content_type_id="modulemd_defaults",
            repository_memberships=["repo1"],
        ),
        ModulemdUnit(
            unit_id="82e2e662-f728-b4fa-4248-5e3a0a5d2f34",
            name="avocado-vt",
            stream="82lts",
            version=3420210902113311,
            context="035be0ad",
            arch="x86_64",
            content_type_id="modulemd",
            repository_memberships=["repo1"],
            artifacts=[
                "avocado-vt-0:82.0-3.module_f34+12808+b491ffc8.src",
                "python3-avocado-vt-0:82.0-3.module_f34+12808+b491ffc8.noarch",
            ],
            profiles={
                "default": {
                    "description": "Common profile installing the avocado-vt plugin.",
                    "rpms": ["python3-avocado-vt"],
                }
            },
            dependencies=[ModulemdDependency(name="avocado", stream="82lts")],
        ),
        ModulemdUnit(
            unit_id="23a7711a-8133-2876-37eb-dcd9e87a1613",
            name="dwm",
            stream="6.0",
            version=3420210201213909,
            context="058368ca",
            arch="x86_64",
            content_type_id="modulemd",
            repository_memberships=["repo1"],
            artifacts=[
                "dwm-0:6.0-1.module_f34+11150+aec78cf8.src",
                "dwm-0:6.0-1.module_f34+11150+aec78cf8.x86_64",
                "dwm-debuginfo-0:6.0-1.module_f34+11150+aec78cf8.x86_64",
                "dwm-debugsource-0:6.0-1.module_f34+11150+aec78cf8.x86_64",
                "dwm-user-0:6.0-1.module_f34+11150+aec78cf8.x86_64",
            ],
            profiles={
                "default": {
                    "description": "The minimal, distribution-compiled dwm binary.",
                    "rpms": ["dwm"],
                },
                "user": {
                    "description": "Includes distribution-compiled dwm as well as a helper script to apply user patches and configuration, dwm-user.",
                    "rpms": ["dwm", "dwm-user"],
                },
            },
            dependencies=[],
        ),
    ]
