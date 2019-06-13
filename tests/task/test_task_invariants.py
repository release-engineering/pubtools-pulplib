import pytest

from pubtools.pulplib import Task


def test_task_impossible_states():
    """It's not possible to create a task where succeeded is True but
    completed is False."""
    with pytest.raises(ValueError):
        Task(id="foobar", succeeded=True, completed=False)
