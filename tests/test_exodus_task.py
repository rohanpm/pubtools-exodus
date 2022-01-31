import pytest

from pubtools.exodus.task import ExodusTask


def test_run(patch_env_vars):
    with pytest.raises(NotImplementedError) as e:
        ExodusTask().run()
