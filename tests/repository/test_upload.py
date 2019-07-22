import logging
import pytest
import json

from pubtools.pulplib import (
    Repository,
    FileRepository,
    Task,
    DetachedException,
    TaskFailedException,
)


def test_upload_detached():
    """publish raises if called on a detached repo"""
    with pytest.raises(DetachedException):
        FileRepository(id="some-repo").upload_file("some-file")


def test_upload_file(client, requests_mocker, tmpdir, caplog):
    """test upload a file to a repo in pulp"""

    logging.getLogger().setLevel(logging.INFO)
    caplog.set_level(logging.INFO)

    repo_id = "repo1"
    repo = FileRepository(id=repo_id)
    repo.__dict__["_client"] = client

    client._CHUNK_SIZE = 20

    request_body = {
        "_href": "/pulp/api/v2/content/uploads/cfb1fed0-752b-439e-aa68-fba68eababa3/",
        "upload_id": "cfb1fed0-752b-439e-aa68-fba68eababa3",
    }
    upload_id = request_body["upload_id"]

    import_report = {
        "result": {},
        "error": {},
        "spawned_tasks": [
            {
                "_href": "/pulp/api/v2/tasks/7744e2df-39b9-46f0-bb10-feffa2f7014b/",
                "task_id": "task1",
            }
        ],
    }

    tasks_report = [{"task_id": "task1", "state": "finished"}]

    somefile = tmpdir.join("some-file.txt")
    somefile.write(b"there is some binary data:\x00\x01\x02")

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/content/uploads/", json=request_body
    )
    requests_mocker.put(
        "https://pulp.example.com/pulp/api/v2/contents/%s/0" % upload_id, json=[]
    )
    requests_mocker.put(
        "https://pulp.example.com/pulp/api/v2/contents/%s/20" % upload_id, json=[]
    )
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/%s/actions/import_upload/"
        % repo_id,
        json=import_report,
    )
    requests_mocker.delete(
        "https://pulp.example.com/pulp/api/v2/content/uploads/%s/" % upload_id, json=[]
    )
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/", json=tasks_report
    )

    # delete's done, return []
    assert repo.upload_file(str(somefile)).result() == []

    # 4th call should be import, check if right unit_key's passed
    import_request = requests_mocker.request_history[3].json()
    import_unit_key = {
        u"name": u"some-file.txt",
        u"digest": u"fad3fc1e6d583b2003ec0a5273702ed8fcc2504271c87c40d9176467ebe218cb",
        u"size": 29,
    }
    assert import_request["unit_key"] == import_unit_key
    messages = caplog.messages

    # 6 reuqests should be made
    assert requests_mocker.call_count == 6
    # task's spwaned and completed
    assert "Created Pulp task: task1" in messages
    assert "Pulp task completed: task1" in messages
