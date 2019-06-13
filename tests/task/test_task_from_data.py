import pytest

from pubtools.pulplib import Task, InvalidDataException


def test_bad_state():
    """from_data raises if input data has bogus state"""
    with pytest.raises(InvalidDataException):
        Task.from_data({"task_id": "abc", "state": "whatever"})


def test_successful_task():
    """from_data sets attributes appropriately for a successful task"""
    task = Task.from_data({"task_id": "some-task", "state": "finished"})
    assert task == Task(id="some-task", completed=True, succeeded=True)


def test_failed_task():
    """from_data sets attributes appropriately for a failed task"""
    task = Task.from_data({"task_id": "some-task", "state": "error"})
    assert task == Task(id="some-task", completed=True, succeeded=False)
