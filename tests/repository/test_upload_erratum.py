from pubtools.pulplib import YumRepository, ErratumUnit, ErratumReference


def test_upload_erratum(client, requests_mocker):
    """An ErratumUnit can be uploaded to a repository using the client."""

    repo_id = "repo1"
    repo = YumRepository(id=repo_id)
    repo.__dict__["_client"] = client

    unit = ErratumUnit(
        id="RHBA-1234:56",
        summary="A great advisory",
        version="1",
        status="final",
        updated="some updated time",
        issued="some issued time",
        description="testing upload",
        pushcount="507",
        from_="noreply@example.com",
        reboot_suggested=False,
        rights="copyright bob",
        content_types=["rpm", "module"],
        references=[
            ErratumReference(
                title="a link",
                href="https://example.com/test-advisory",
                type="self",
                id="self-id",
            )
        ],
        pkglist=[],
    )

    # Set up the requests it'll do:
    #
    # It will request an upload
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/content/uploads/",
        json={"upload_id": "my-upload-123"},
    )

    # It'll do an import against that upload
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/repo1/actions/import_upload/",
        json={"spawned_tasks": [{"task_id": "task123"}, {"task_id": "task234"}]},
    )

    # It'll search for status of the import tasks
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/",
        json=[
            {"task_id": "task123", "state": "finished"},
            {"task_id": "task234", "state": "finished"},
        ],
    )

    # It'll clean up the upload
    requests_mocker.delete(
        "https://pulp.example.com/pulp/api/v2/content/uploads/my-upload-123/"
    )

    # Mocker setup is complete.

    # It should start the upload OK
    upload_f = repo.upload_erratum(unit)

    # I can await the result
    tasks = upload_f.result()

    # There should be the two tasks returned from the API
    assert sorted([t.id for t in tasks]) == ["task123", "task234"]

    # Each task should be successful
    for t in tasks:
        assert t.completed
        assert t.succeeded

    # What did the client actually try to import?
    import_request = requests_mocker.request_history[1]

    assert import_request.json() == {
        "upload_id": "my-upload-123",
        "unit_type_id": "erratum",
        "unit_key": {"id": "RHBA-1234:56"},
        "unit_metadata": {
            # This should contain an accurate serialization of all fields
            # into the form required by Pulp.
            "id": "RHBA-1234:56",
            "version": "1",
            "status": "final",
            "updated": "some updated time",
            "issued": "some issued time",
            "description": "testing upload",
            "pushcount": "507",
            "reboot_suggested": False,
            "from": "noreply@example.com",
            "rights": "copyright bob",
            "summary": "A great advisory",
            "pulp_user_metadata": {"content_types": ["rpm", "module"]},
            "references": [
                {
                    "href": "https://example.com/test-advisory",
                    "id": "self-id",
                    "title": "a link",
                    "type": "self",
                }
            ],
            "pkglist": [],
            # Note also that fields not explicitly set will be serialized
            # as None (see doc string on upload_erratum).
            "title": None,
            "severity": None,
            "release": None,
            "type": None,
            "solution": None,
        },
    }
