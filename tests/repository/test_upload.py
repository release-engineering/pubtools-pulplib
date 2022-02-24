# -*- coding: utf-8 -*-
import logging
import time
import pytest
import json

from six.moves import StringIO

from pubtools.pulplib import (
    Repository,
    FileRepository,
    Task,
    DetachedException,
    TaskFailedException,
)

from pubtools.pulplib._impl.log import TimedLogger
from pubtools.pulplib._impl.client import client

from ..ioutil import ZeroesIO


@pytest.fixture()
def fast_timed_logger(monkeypatch):
    # Force TimedLogger class to use an interval of 0 (i.e. it logs every time).
    # Tests otherwise will run too fast for any of the log messages to ever
    # be produced.

    class FastTimedLogger(TimedLogger):
        def __init__(self):
            super(FastTimedLogger, self).__init__(interval=0)

    monkeypatch.setattr(client, "TimedLogger", FastTimedLogger)


def test_upload_detached():
    """upload_file raises if called on a detached repo"""
    with pytest.raises(DetachedException):
        FileRepository(id="some-repo").upload_file("some-file")


def test_upload_file(client, requests_mocker, tmpdir, caplog, fast_timed_logger):
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
        "spawned_tasks": [{"_href": "/pulp/api/v2/tasks/task1/", "task_id": "task1"}],
    }

    tasks_report = [{"task_id": "task1", "state": "finished"}]

    somefile = tmpdir.join("some-file.txt")
    somefile.write(b"there is some binary data:\x00\x01\x02")

    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/content/uploads/", json=request_body
    )
    requests_mocker.put(
        "https://pulp.example.com/pulp/api/v2/content/uploads/%s/0/" % upload_id,
        json=[],
    )
    requests_mocker.put(
        "https://pulp.example.com/pulp/api/v2/content/uploads/%s/20/" % upload_id,
        json=[],
    )
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/repositories/%s/actions/import_upload/"
        % repo_id,
        json=import_report,
    )
    requests_mocker.post(
        "https://pulp.example.com/pulp/api/v2/tasks/search/", json=tasks_report
    )
    requests_mocker.delete(
        "https://pulp.example.com/pulp/api/v2/content/uploads/%s/" % upload_id, json=[]
    )

    assert repo.upload_file(str(somefile)).result() == [
        Task(id="task1", succeeded=True, completed=True)
    ]

    # the 6th request call might not be done in time, try 1000
    # times with .01 sec sleep before next try.
    for i in range(1000):
        time.sleep(0.01)
        try:
            assert requests_mocker.call_count == 6
        except AssertionError:
            if i != 999:
                continue
            else:
                raise
        else:
            break

    # 4th call should be import, check if right unit_key's passed
    import_request = requests_mocker.request_history[3].json()
    import_unit_key = {
        u"name": somefile.basename,
        u"checksum": u"fad3fc1e6d583b2003ec0a5273702ed8fcc2504271c87c40d9176467ebe218cb",
        u"size": 29,
    }
    assert import_request["unit_key"] == import_unit_key

    messages = caplog.messages

    # It should tell us about the upload
    assert (
        "Uploading some-file.txt to repo1 [cfb1fed0-752b-439e-aa68-fba68eababa3]"
        in messages
    )

    # It should log some progress info during the upload.
    # (Note these logs would not normally be produced for such a small amount of
    # progress - it's only because we have reduced the logging interval for testing)
    assert (
        "Still uploading some-file.txt: 20 Bytes / 68% [cfb1fed0-752b-439e-aa68-fba68eababa3]"
        in messages
    )
    assert (
        "Still uploading some-file.txt: 29 Bytes / 100% [cfb1fed0-752b-439e-aa68-fba68eababa3]"
        in messages
    )

    # task's spawned and completed
    assert "Created Pulp task: task1" in messages
    assert "Pulp task completed: task1" in messages


@pytest.mark.parametrize(
    "relative_url,expected",
    [
        ("some/path/", "some/path/some-file.txt"),
        ("some/path/foo.txt", "some/path/foo.txt"),
    ],
)
def test_get_relative_url(tmpdir, relative_url, expected):
    somefile = tmpdir.join("some-file.txt")
    repo = FileRepository(id="some-repo")
    result = repo._get_relative_url(str(somefile), relative_url)

    assert result == expected


def test_get_relative_url_with_file_object(tmpdir):
    repo = FileRepository(id="some-repo")
    file_obj = StringIO()

    with pytest.raises(ValueError):
        repo._get_relative_url(file_obj, None)

    with pytest.raises(ValueError):
        repo._get_relative_url(file_obj, "some/path/")

    assert repo._get_relative_url(file_obj, "path/foo.txt") == "path/foo.txt"


def test_upload_file_contains_unicode(client, requests_mocker):
    file_obj = StringIO("哈罗")
    upload_id = "cfb1fed0-752b-439e-aa68-fba68eababa3"

    requests_mocker.put(
        "https://pulp.example.com/pulp/api/v2/content/uploads/%s/0/" % upload_id,
        json=[],
    )

    repo_id = "repo1"
    repo = FileRepository(id=repo_id)
    repo.__dict__["_client"] = client

    upload_f = client._do_upload_file(upload_id, file_obj)

    assert upload_f.result() == (
        "478f4808df7898528c7f13dc840aa321c4109f5c9f33bad7afcffc0253d4ff8f",
        6,
    )


def test_upload_file_verylarge(client, requests_mocker):
    """Client can upload a 2GB file successfully."""

    file_size = 2000000000
    file_obj = ZeroesIO(file_size)

    upload_id = "cfb1fed0-752b-439e-aa68-fba68eababa3"

    # We will be uploading many chunks and we need to mock the 'offset' for each one...
    # Note this must align with the client's internal CHUNK_SIZE.
    chunk_size = 1024 * 1024
    for i in range(0, 3000):
        requests_mocker.put(
            "https://pulp.example.com/pulp/api/v2/content/uploads/%s/%d/"
            % (upload_id, i * chunk_size),
            json=[],
        )

    repo_id = "repo1"
    repo = FileRepository(id=repo_id)
    repo.__dict__["_client"] = client

    # It should be able to upload successfully.
    upload_f = client._do_upload_file(upload_id, file_obj)

    assert upload_f.result() == (
        # We should get the right checksum and size back, which proves all
        # the data was read correctly.
        #
        # If you want to verify this checksum, try:
        #
        #   dd if=/dev/zero bs=1000000 count=2000 status=none | sha256sum
        #
        "2e0c654b6cba3a1e816726bae0eac481eb7fd0351633768c3c18392e0f02b619",
        file_size,
    )
