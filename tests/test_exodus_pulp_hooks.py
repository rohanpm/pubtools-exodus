import json
import logging
import os

from pubtools.pluggy import pm, task_context

from .conftest import FakePublishOptions


def test_exodus_pulp_typical(successful_gw_task, monkeypatch, caplog):
    monkeypatch.setenv("EXODUS_ENABLED", "True")
    url = os.getenv("EXODUS_GW_URL")
    env = os.getenv("EXODUS_GW_ENV")

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
            "created exodus-gw publish 497f6eca-6276-4993-bfeb-53cbbbba6f08"
            in caplog.text
        )
        # The pre-publish hook should've returned options with exodus-publish
        # arg appended to existing rsync_extra_args.
        assert hook_rets[0] == FakePublishOptions(
            rsync_extra_args=[
                "--existing-arg",
                "--exodus-publish=497f6eca-6276-4993-bfeb-53cbbbba6f08",
            ],
        )

        # Simulate completion of pulp publish; call task pulp flush
        pm.hook.task_pulp_flush()

        assert (
            "committed exodus-gw publish: %s"
            % json.dumps(
                successful_gw_task["commit"]["response"], sort_keys=True
            )
            in caplog.text
        )


def test_exodus_pulp_no_publish(successful_gw_task, monkeypatch, caplog):
    monkeypatch.setenv("EXODUS_ENABLED", "True")
    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    with task_context():
        pm.hook.task_pulp_flush()

        assert "no exodus-gw publish to commit" in caplog.text


def test_exodus_pulp_disabled(successful_gw_task, monkeypatch, caplog):
    monkeypatch.setenv("EXODUS_ENABLED", "False")
    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    with task_context():
        # With Exodus disabled, this should be a no-op.
        pm.hook.pulp_repository_pre_publish(repository=None, options={})

    assert caplog.text == ""
