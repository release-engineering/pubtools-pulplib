import pytest
import datetime

from pubtools.pulplib import FileUnit


def test_update_no_id(requests_mocker, client):
    # Try to update something with no ID; it should fail immediately
    # (no future) as we can't even try to update without an ID.
    with pytest.raises(ValueError) as excinfo:
        client.update_content(
            FileUnit(
                path="x",
                size=0,
                sha256sum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            )
        )

    # It should tell us why
    assert "unit_id missing on call to update_content()" in str(excinfo.value)


def test_can_update_content(requests_mocker, client):
    requests_mocker.put(
        "https://pulp.example.com/pulp/api/v2/content/units/iso/some-unit/pulp_user_metadata/",
        # Note: passing json=None here doesn't work as requests_mocker seems
        # unable to differentiate between "json should be None" and "no json response
        # is specified".
        text="null",
        headers={"Content-Type": "application/json"},
    )

    unit = FileUnit(
        unit_id="some-unit",
        description="A unit I'm about to update",
        cdn_published=datetime.datetime(2021, 12, 6, 11, 19, 0),
        path="x",
        size=0,
        sha256sum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )

    update_f = client.update_content(unit)

    # It should succeed.
    update_f.result()

    # It should have done a single request.
    assert len(requests_mocker.request_history) == 1

    req = requests_mocker.request_history[0]

    # Should have been a PUT to the appropriate API.
    assert req.method == "PUT"
    assert (
        req.url
        == "https://pulp.example.com/pulp/api/v2/content/units/iso/some-unit/pulp_user_metadata/"
    )

    # Should have included all the usermeta fields in request body.
    assert req.json() == {
        "cdn_path": None,
        "cdn_published": "2021-12-06T11:19:00Z",
        "description": "A unit I'm about to update",
    }


def test_update_content_fails(requests_mocker, client):
    requests_mocker.put(
        "https://pulp.example.com/pulp/api/v2/content/units/iso/some-unit/pulp_user_metadata/",
        status_code=400,
    )

    unit = FileUnit(
        unit_id="some-unit",
        description="A unit I'm about to update",
        cdn_path="/some/path.txt",
        path="x",
        size=0,
        sha256sum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )

    update_f = client.update_content(unit)

    # It should fail, since the HTTP request failed.
    assert "400 Client Error" in str(update_f.exception())
