import logging

from pubtools.pluggy import pm, task_context

from .conftest import FakePublishOptions


def test_exodus_pulp_typical(successful_gw_task, caplog):
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
            ],
        )

        # Simulate completion of pulp publish; call task pulp flush
        pm.hook.task_pulp_flush()

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


def test_exodus_pulp_no_publish(patch_env_vars, caplog):
    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    with task_context():
        pm.hook.task_pulp_flush()

        assert "No exodus-gw publish to commit" in caplog.text


def test_exodus_pulp_disabled(monkeypatch, caplog):
    monkeypatch.setenv("EXODUS_ENABLED", "False")
    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    with task_context():
        # With Exodus disabled, this should be a no-op.
        pm.hook.pulp_repository_pre_publish(repository=None, options={})

    assert caplog.text == ""
