import logging

import pytest
from pubtools.pluggy import pm, task_context

from .conftest import FakePublishOptions


@pytest.mark.parametrize(
    "commit_hook_name,commit_hook_args",
    [("task_pulp_flush", dict()), ("task_stop", dict(failed=False))],
)
def test_exodus_pulp_typical(
    successful_gw_task, commit_hook_name, commit_hook_args, caplog
):
    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    # Simulate task start
    with task_context():
        # Simulate repo publish; call prep-publish hook
        hook_rets = pm.hook.pulp_repository_pre_publish(
            repository=None,
            options=FakePublishOptions(rsync_extra_args=["--existing-arg"]),
        )
        hook_rets = [ret for ret in hook_rets if ret is not None]

        assert (
            "Created exodus-gw publish 497f6eca-6276-4993-bfeb-53cbbbba6f08"
            in caplog.text
        )
        # The pre-publish hook should've returned options with exodus-publish
        # arg appended to existing rsync_extra_args.
        assert hook_rets[0] == FakePublishOptions(
            rsync_extra_args=[
                "--existing-arg",
                "--exodus-publish=497f6eca-6276-4993-bfeb-53cbbbba6f08",
                "--exodus-commit=phase1",
            ],
        )

        # Trigger whichever hook is expected to make commit happen
        hook = getattr(pm.hook, commit_hook_name)
        hook(**commit_hook_args)

        assert (
            "Committing exodus-gw publish 497f6eca-6276-4993-bfeb-53cbbbba6f08"
            in caplog.text
        )
        assert (
            "exodus-gw commit 9187ec3d-ba51-4a3b-9298-e534b0869350 to "
            "https://exodus-gw.test.redhat.com complete" in caplog.text
        )
        assert (
            "Committed exodus-gw publish 497f6eca-6276-4993-bfeb-53cbbbba6f08"
            in caplog.text
        )


def test_exodus_pulp_phase1_disabled(
    successful_gw_task, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("EXODUS_PULP_HOOK_PHASE1_COMMIT", "0")

    with task_context():
        hook_rets = pm.hook.pulp_repository_pre_publish(
            repository=None,
            options=FakePublishOptions(rsync_extra_args=["--existing-arg"]),
        )
        hook_rets = [ret for ret in hook_rets if ret is not None]

        # The pre-publish hook should've returned options with exodus-publish
        # arg appended to existing rsync_extra_args, but this time it should
        # NOT have added exodus-commit due to the above env var.
        assert hook_rets[0] == FakePublishOptions(
            rsync_extra_args=[
                "--existing-arg",
                "--exodus-publish=497f6eca-6276-4993-bfeb-53cbbbba6f08",
            ],
        )


def test_exodus_pulp_no_publish(patch_env_vars, caplog):
    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    with task_context():
        pm.hook.task_pulp_flush()

        assert "No exodus-gw publish to commit" in caplog.text


def test_exodus_pulp_disabled_global(monkeypatch, caplog):
    """Tests disablement of hook via global EXODUS_ENABLED var."""
    monkeypatch.setenv("EXODUS_ENABLED", "False")
    caplog.set_level(logging.INFO, "pubtools-exodus")

    with task_context():
        # With Exodus disabled, this should be a no-op.
        pm.hook.pulp_repository_pre_publish(repository=None, options={})

    # Should not have generated anything INFO or higher.
    assert caplog.text == ""


def test_exodus_pulp_disabled_hook(monkeypatch, caplog):
    """Tests disablement of hook via hook-specific var."""
    monkeypatch.setenv("EXODUS_ENABLED", "True")
    monkeypatch.setenv("EXODUS_PULP_HOOK_ENABLED", "0")
    caplog.set_level(logging.INFO, "pubtools-exodus")

    with task_context():
        # With Exodus disabled, this should be a no-op.
        pm.hook.pulp_repository_pre_publish(repository=None, options={})

    # Should not have generated anything INFO or higher.
    assert caplog.text == ""
