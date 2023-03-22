from datetime import datetime
import logging

import pytest
from more_executors.futures import f_return
from mock import patch, Mock, call
from requests.exceptions import HTTPError

from pubtools.pulplib._impl.model.repository.repo_lock import RepoLock, LockClaim
from pubtools.pulplib import Client, FakeController, Repository


@pytest.fixture
def mock_client():
    client = Client("https://pulp.example.com/")
    client._request_executor.submit = Mock()
    client._do_request = "do_request_func"
    return client


def pulp_get_response(key_values):
    return f_return({"notes": key_values})


def pulp_put_response():
    return f_return({})


@patch("pubtools.pulplib._impl.model.repository.repo_lock.now")
@patch("pubtools.pulplib._impl.model.repository.repo_lock.random")
def test_repo_lock(random_mock, datetime_mock, mock_client):
    datetime_mock.side_effect = [
        datetime.fromtimestamp(1000.0),
        datetime.fromtimestamp(1060.0),
        datetime.fromtimestamp(1120.0),
        datetime.fromtimestamp(1120.0),
        datetime.fromtimestamp(1120.0),
        datetime.fromtimestamp(1180.0),
    ]
    random_mock.choices = Mock(return_value="1234")
    # Pulp API Calls
    # 1. Get the current locks to check if three's stale ones. None this time.
    # 2. Put our lock in the repo notes.
    # 3. Get the current locks to check if it's our turn to run. (not yet)
    # 3. Get the current locks again, it's our turn this time.
    # 4. Delete the lock from the repo notes.
    mock_client._request_executor.submit.side_effect = [
        pulp_get_response({}),  # 1
        pulp_put_response(),  # 2
        pulp_get_response(
            {
                "pulplib-lock-claim-1233": '{"id": "1233", "context": "testing repo lock", "created": 900.0, "valid_from": 910.0, "expires": 1900.0}',
                "pulplib-lock-claim-1234": '{"id": "1234", "context": "testing repo lock", "created": 1000.0, "valid_from": 1010.0, "expires": 2000.0}',
            }
        ),  # 3
        pulp_get_response(
            {
                "pulplib-lock-claim-1234": '{"id": "1234", "context": "testing repo lock", "created": 1000.0, "valid_from": 1010.0, "expires": 2000.0}'
            }
        ),  # 4
        pulp_put_response(),  # 5
    ]
    expected_endpoint = "https://pulp.example.com/pulp/api/v2/repositories/test-repo/"
    expected_mock_calls = [
        call("do_request_func", url=expected_endpoint, method="GET"),
        call(
            "do_request_func",
            url=expected_endpoint,
            method="PUT",
            json={
                "delta": {
                    "notes": {
                        "pulplib-lock-claim-1234": '{"id": "1234", "context": "testing repo lock", "created": 1000.0, "valid_from": 1010.0, "expires": 2000.0}'
                    }
                }
            },
        ),
        call("do_request_func", url=expected_endpoint, method="GET"),
        call("do_request_func", url=expected_endpoint, method="GET"),
        call(
            "do_request_func",
            url=expected_endpoint,
            method="PUT",
            json={"delta": {"notes": {"pulplib-lock-claim-1234": None}}},
        ),
    ]
    lock = RepoLock(
        "test-repo",
        mock_client,
        "testing repo lock",
        1000,
    )

    # Runs __enter__ and __exit__ in RepoLock
    with lock:
        pass

    mock_client._request_executor.submit.assert_has_calls(expected_mock_calls)
    assert mock_client._request_executor.submit.call_count == 5


@patch("pubtools.pulplib._impl.model.repository.repo_lock.now")
@patch("pubtools.pulplib._impl.model.repository.repo_lock.random")
def test_repo_lock_fake_client(random_mock, datetime_mock):
    datetime_mock.side_effect = [
        datetime.fromtimestamp(1000.0),
        datetime.fromtimestamp(1060.0),
        datetime.fromtimestamp(1120.0),
        datetime.fromtimestamp(1180.0),
    ]
    random_mock.choices = Mock(return_value="1234")
    ctrl = FakeController()
    ctrl.insert_repository(Repository(id="test-repo"))
    lock = ctrl.new_client().get_repository("test-repo").lock("test")

    # Runs __enter__ and __exit__ in RepoLock
    with lock:
        pass

    lock_history = ctrl.repo_lock_history
    assert len(lock_history) == 2
    assert lock_history[0].repository == "test-repo"
    assert lock_history[0].action == "lock"
    assert lock_history[1].repository == "test-repo"
    assert lock_history[1].action == "unlock"


@patch("pubtools.pulplib._impl.model.repository.repo_lock.now")
def test_remove_expired_locks(datetime_mock, mock_client):
    datetime_mock.return_value = datetime.fromtimestamp(3000.0)

    mock_client._request_executor.submit.side_effect = [
        pulp_get_response(
            {
                "pulplib-lock-claim-1234": '{"id": "1234", "context": "testing repo lock", "created": 1000.0, "valid_from": 1010.0, "expires": 2000.0}',
                "pulplib-lock-claim-1235": '{"id": "1235", "context": "testing repo lock", "created": 1000.0, "valid_from": 1010.0, "expires": 2000.0}',
            }
        ),
        pulp_put_response(),
    ]
    expected_endpoint = "https://pulp.example.com/pulp/api/v2/repositories/test-repo/"
    expected_mock_calls = [
        call("do_request_func", url=expected_endpoint, method="GET"),
        call(
            "do_request_func",
            url=expected_endpoint,
            method="PUT",
            json={
                "delta": {
                    "notes": {
                        "pulplib-lock-claim-1234": None,
                        "pulplib-lock-claim-1235": None,
                    }
                }
            },
        ),
    ]
    lock = RepoLock(
        "test-repo",
        mock_client,
        "testing repo lock",
        1000,
    )

    lock.remove_expired_locks()
    mock_client._request_executor.submit.assert_has_calls(expected_mock_calls)


@patch("pubtools.pulplib._impl.model.repository.repo_lock.now")
def test_remove_expired_locks_fake_client(datetime_mock):
    datetime_mock.return_value = datetime.fromtimestamp(3000.0)
    ctrl = FakeController()
    ctrl.insert_repository(Repository(id="test-repo"))
    client = ctrl.new_client()
    client._update_repo_lock_data(
        "test-repo",
        {
            "pulplib-lock-claim-1234": '{"id": "1234", "context": "testing repo lock", "created": 1000.0, "valid_from": 1010.0, "expires": 2000.0}'
        },
    )
    client._update_repo_lock_data(
        "test-repo",
        {
            "pulplib-lock-claim-1235": '{"id": "1235", "context": "testing repo lock", "created": 1000.0, "valid_from": 1010.0, "expires": 2000.0}'
        },
    )

    client.get_repository("test-repo").lock("test").remove_expired_locks()

    lock_history = ctrl.repo_lock_history
    assert len(lock_history) == 3
    assert lock_history[0].repository == "test-repo"
    assert lock_history[0].action == "lock"
    assert lock_history[1].repository == "test-repo"
    assert lock_history[1].action == "lock"
    assert lock_history[2].repository == "test-repo"
    assert lock_history[2].action == "multi-unlock"


@patch("pubtools.pulplib._impl.model.repository.repo_lock.now")
def test_remove_expired_locks_error(datetime_mock, mock_client, caplog):
    # We may cause an error if we try to delete a lock which has already been
    # deleted. This may happen if another task runs clean up at the same time.
    mock_response = Mock()
    mock_response.json.return_value = {
        "exception": ["KeyError: 'pulplib-lock-claim-1234'\n"]
    }
    mock_client._update_repo_lock_data = Mock(
        side_effect=HTTPError(response=mock_response)
    )
    datetime_mock.return_value = datetime.fromtimestamp(3000.0)

    mock_client._request_executor.submit.side_effect = [
        pulp_get_response(
            {
                "pulplib-lock-claim-1234": '{"id": "1234", "context": "testing repo lock", "created": 1000.0, "valid_from": 1010.0, "expires": 2000.0}',
                "pulplib-lock-claim-1235": '{"id": "1235", "context": "testing repo lock", "created": 1000.0, "valid_from": 1010.0, "expires": 2000.0}',
            }
        ),
    ]

    lock = RepoLock(
        "test-repo",
        mock_client,
        "testing repo lock",
        1000,
    )

    lock.remove_expired_locks()

    assert (
        "An error occurred while trying to delete an expired lock. The locks have already been deleted"
        in caplog.messages
    )


def test_exception_handling_on_lock_delete(mock_client):
    mock_response = Mock()
    mock_response.json.return_value = {
        "exception": ["KeyError: 'pulplib-lock-claim-1234'\n"]
    }
    mock_client._update_repo_lock_data = Mock(
        side_effect=HTTPError(response=mock_response)
    )
    expected_mock_calls = [
        call("test-repo", {"pulplib-lock-claim-1234": None}, await_result=True)
    ]
    lock = RepoLock(
        "test-repo",
        mock_client,
        "testing repo lock",
        1000,
    )
    lock._lock_claim = LockClaim.from_json_data(
        {
            "id": "1234",
            "context": "test",
            "created": 1000.0,
            "valid_from": 1010.0,
            "expires": 2000.0,
        }
    )

    lock.delete_lock_claim()

    mock_client._update_repo_lock_data.assert_has_calls(expected_mock_calls)


@patch("pubtools.pulplib._impl.model.repository.repo_lock.now")
@patch("pubtools.pulplib._impl.model.repository.repo_lock.random")
def test_repo_log_error_on_stale_lock(random_mock, datetime_mock, caplog):
    # If we've held the lock for too long, there should be an error reported.
    datetime_mock.side_effect = [
        datetime.fromtimestamp(1000.0),
        datetime.fromtimestamp(1060.0),
        datetime.fromtimestamp(1120.0),
        datetime.fromtimestamp(5000.0),
        datetime.fromtimestamp(5000.0),
    ]
    random_mock.choices = Mock(return_value="1234")
    ctrl = FakeController()
    ctrl.insert_repository(Repository(id="test-repo"))
    lock = ctrl.new_client().get_repository("test-repo").lock("test")

    # Runs __enter__ and __exit__ in RepoLock
    with lock:
        pass

    # Should have logged an error.
    assert (
        "Client requested lock on repo test-repo for 1800 seconds but was held for 4000 seconds (test)"
        in caplog.messages
    )
