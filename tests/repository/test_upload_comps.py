from io import BytesIO
from xml.parsers.expat import ExpatError

import pytest

from pubtools.pulplib import YumRepository


def test_upload_comps_xml(client, requests_mocker):
    """A client can upload expected units from within a comps.xml."""

    repo_id = "repo1"
    repo = YumRepository(id=repo_id)
    repo.__dict__["_client"] = client

    # Some XML to upload.
    # This is fairly minimal as this test focuses on upload functionality.
    # There are other tests exercising the XML parser more thoroughly.
    xml = BytesIO(
        b"""
        <comps>
            <group>
                <id>3d-printing</id>
                <name>3D Printing</name>
                <name xml:lang="af">3D-drukwerk</name>
                <description>3D printing software</description>
                <packagelist>
                    <packagereq type="default">admesh</packagereq>
                    <packagereq>blender</packagereq>
                </packagelist>
            </group>

            <category>
                <id>kde-desktop-environment</id>
                <name>KDE Desktop</name>
                <display_order>10</display_order>
                <grouplist>
                    <groupid>kde-office</groupid>
                    <groupid>kde-telepathy</groupid>
                </grouplist>
            </category>


            <environment>
                <id>basic-desktop-environment</id>
                <name>Basic Desktop</name>
                <name xml:lang="af">Basiese werkskerm</name>
                <description>X Window System with a choice of window manager.</description>
                <grouplist>
                    <groupid>networkmanager-submodules</groupid>
                    <groupid>standard</groupid>
                </grouplist>
                <optionlist>
                    <groupid default="true">xmonad</groupid>
                    <groupid>xmonad-mate</groupid>
                </optionlist>
            </environment>

            <langpacks>
                <match install="stardict-dic-%s" name="stardict"/>
                <match install="tkgate-%s" name="tkgate"/>
            </langpacks>
        </comps>
    """
    )

    # Set up the requests it'll do:
    #
    # It should unassociate previous units
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/repo1/actions/unassociate/",
        json={"spawned_tasks": [{"task_id": "remove-task"}]},
    )

    # It'll search for the status of tasks.
    # Note: to avoid an overly complex mock we just let every task search return all
    # tasks rather than differentiating between remove and upload tasks
    upload_count = 4
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        json=[{"task_id": "remove-task", "state": "finished"}]
        + [
            {"task_id": "upload-task-%d" % i, "state": "finished"}
            for i in range(0, upload_count)
        ],
    )

    # It will request various uploads
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/content/uploads/",
        [{"json": {"upload_id": "upload-%d" % i}} for i in range(0, upload_count)],
    )

    # It'll do an import against the uploads
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/repo1/actions/import_upload/",
        [
            {"json": {"spawned_tasks": [{"task_id": "upload-task-%d" % i}]}}
            for i in range(0, upload_count)
        ],
    )

    # It'll clean up the uploads
    for i in range(0, upload_count):
        requests_mocker.delete(
            "https://pulp.example.com/pulp/api/v2/content/uploads/upload-%d/" % i
        )

    # Mocker setup is complete.

    # It should start the upload OK
    upload_f = repo.upload_comps_xml(xml)

    # I can await the result
    tasks = upload_f.result()

    # There should be various tasks returned from the API
    assert sorted([t.id for t in tasks]) == [
        "upload-task-0",
        "upload-task-1",
        "upload-task-2",
        "upload-task-3",
    ]

    # Each task should be successful
    for t in tasks:
        assert t.completed
        assert t.succeeded

    # Gather info on exactly what the client imported
    imported_units = []
    for req in requests_mocker.request_history:
        if req.url.endswith("/import_upload/"):
            imported_units.append(req.json()["unit_metadata"])

    imported_units.sort(key=lambda u: u["_content_type_id"])

    # Did we import exactly the expected units?
    assert imported_units == [
        {
            "_content_type_id": "package_category",
            "id": "kde-desktop-environment",
            "name": "KDE Desktop",
            "display_order": 10,
            "packagegroupids": ["kde-office", "kde-telepathy"],
            "repo_id": "repo1",
        },
        {
            "_content_type_id": "package_environment",
            "id": "basic-desktop-environment",
            "name": "Basic Desktop",
            "translated_name": {"af": "Basiese werkskerm"},
            "description": "X Window System with a choice of window manager.",
            "group_ids": ["networkmanager-submodules", "standard"],
            "options": [
                {"group": "xmonad", "default": True},
                {"group": "xmonad-mate", "default": False},
            ],
            "repo_id": "repo1",
        },
        {
            "_content_type_id": "package_group",
            "id": "3d-printing",
            "name": "3D Printing",
            "translated_name": {"af": "3D-drukwerk"},
            "description": "3D printing software",
            "default_package_names": ["admesh"],
            "mandatory_package_names": ["blender"],
            "repo_id": "repo1",
        },
        {
            "_content_type_id": "package_langpacks",
            "matches": [
                {"install": "stardict-dic-%s", "name": "stardict"},
                {"install": "tkgate-%s", "name": "tkgate"},
            ],
            "repo_id": "repo1",
        },
    ]


def test_upload_empty_comps_xml(client, requests_mocker):
    """A client can upload an empty comps.xml, which merely removes existing units."""

    repo_id = "repo1"
    repo = YumRepository(id=repo_id)
    repo.__dict__["_client"] = client

    xml = BytesIO(b"<comps/>")

    # Set up the requests it'll do:
    #
    # It should unassociate previous units
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/repo1/actions/unassociate/",
        json={"spawned_tasks": [{"task_id": "remove-task"}]},
    )

    # It'll search for the status of tasks.
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        json=[{"task_id": "remove-task", "state": "finished"}],
    )

    # And... that's it.

    # It should start the upload OK
    upload_f = repo.upload_comps_xml(xml)

    # I can await the result
    tasks = upload_f.result()

    # It should just return the removal task
    assert [t.id for t in tasks] == ["remove-task"]
    assert tasks[0].completed
    assert tasks[0].succeeded

    # Check exactly the removed types
    assert requests_mocker.request_history[0].json() == {
        "criteria": {
            "type_ids": [
                "package_group",
                "package_category",
                "package_environment",
                "package_langpacks",
            ]
        }
    }


def test_bad_comps_xml(client, requests_mocker, tmpdir):
    """A client requested to upload an invalid comps.xml will raise immediately
    without making any requests to Pulp."""

    repo_id = "repo1"
    repo = YumRepository(id=repo_id)
    repo.__dict__["_client"] = client

    comps_xml = tmpdir.join("comps.xml")
    comps_xml.write(b"Oops not valid comps")

    # It should raise
    with pytest.raises(ExpatError):
        repo.upload_comps_xml(str(comps_xml))

    # As we did not register anything in requests_mocker, we've already
    # implicitly tested that no requests happened. But just to be clear...
    assert not requests_mocker.request_history
