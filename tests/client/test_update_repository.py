import pytest
import datetime

from pubtools.pulplib import FileRepository


def test_can_update_repo(requests_mocker, client):
    requests_mocker.put(
        "https://pulp.example.com/pulp/api/v2/repositories/my-repo/",
        text="null",
        headers={"Content-Type": "application/json"},
    )

    repo = FileRepository(
        id="my-repo", eng_product_id=123, product_versions=["1.0", "1.1"]
    )

    update_f = client.update_repository(repo)

    # It should succeed.
    update_f.result()

    # It should have done a single request.
    assert len(requests_mocker.request_history) == 1

    req = requests_mocker.request_history[0]

    # Should have been a PUT to the appropriate API.
    assert req.method == "PUT"
    assert req.url == "https://pulp.example.com/pulp/api/v2/repositories/my-repo/"

    # Should have requested exactly this update - only the mutable notes
    assert req.json() == {
        "delta": {
            "notes": {
                "include_in_download_service": "False",
                "include_in_download_service_preview": "False",
                # Note the serialization into embedded JSON here.
                "product_versions": '["1.0","1.1"]',
            }
        }
    }


def test_update_repo_fails(requests_mocker, client):
    requests_mocker.put(
        "https://pulp.example.com/pulp/api/v2/repositories/my-repo/", status_code=400
    )

    repo = FileRepository(
        id="my-repo", eng_product_id=123, product_versions=["1.0", "1.1"]
    )

    update_f = client.update_repository(repo)

    # It should fail, since the HTTP request failed.
    assert "400 Client Error" in str(update_f.exception())
