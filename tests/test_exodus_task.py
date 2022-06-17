import mock
import pytest

from pubtools.exodus.task import ExodusTask


def test_run():
    with pytest.raises(NotImplementedError) as e:
        ExodusTask().run()


# Mock argv or pytest arguments will be captured.
@mock.patch("sys.argv", [""])
def test_exodus_task_args():
    task = ExodusTask()

    # Should have basic args
    assert task.args.__dict__ == {"debug": False, "verbose": 0}
    # Should have no extra_args
    assert task.extra_args == []

    # Reset extra_args, simulating case in which task.args isn't called
    task._extra_args = None
    # Calling extra_args should change value to empty list
    assert task.extra_args == []
