import io
import logging
import os

import mock
import pytest
from pushsource import PushItem, Source
from six import u

from pubtools.exodus._tasks.push import ExodusPushTask, doc_parser, entry_point

TEST_DATA = os.path.join(os.path.dirname(__file__), "test_data", "exodus_push")


def test_exodus_push_task_args():
    task = ExodusPushTask(args=["staged:/some/path"])

    # Should have basic args
    assert task.args.__dict__ == {
        "debug": False,
        "verbose": 0,
        "source": "staged:/some/path",
    }
    # Should have no extra_args
    assert task.extra_args == []


@mock.patch(
    "sys.argv",
    ["", "--debug", "staged:%s" % os.path.join(TEST_DATA, "source-1")],
)
@mock.patch("pubtools.exodus._tasks.push.ExodusPushTask.run")
def test_exodus_push_entry_point(mock_run, patch_env_vars):
    entry_point()
    assert mock_run.call_count == 1


@mock.patch("pubtools.exodus._tasks.push.ExodusPushTask")
def test_exodus_push_doc_parser(mock_push_task):
    doc_parser()
    assert mock_push_task.call_count == 1


@pytest.mark.parametrize("exodus_enabled", [True, None])
@mock.patch("pubtools.exodus._tasks.push.subprocess.Popen")
def test_exodus_push_typical(
    mock_popen, exodus_enabled, successful_gw_task, caplog, monkeypatch
):
    if exodus_enabled == None:
        monkeypatch.setenv("EXODUS_ENABLED", "")

    mock_popen.return_value.stdout = io.StringIO(
        u("fake exodus-rsync output\nfake task info\n")
    )
    mock_popen.return_value.wait.return_value = 0

    src = os.path.join(TEST_DATA, "source-1")
    args = [
        "--debug",
        "-vvv",
        "--dry-run",
        "staged:%s" % src,
        "--exodus-conf",
        "/path/to/my-conf",
    ]
    caplog.set_level(logging.DEBUG, "pubtools-exodus")
    cmds = [
        [
            "exodus-rsync",
            "--exodus-publish",
            "497f6eca-6276-4993-bfeb-53cbbbba6f08",
            "--exclude",
            ".nfs*",
            "--exclude",
            ".latest_rsync",
            "--exclude",
            ".lock",
            os.path.join(src, "kickstart-repo-x86_64", "RAW"),
            "exodus:kickstart-repo-x86_64",
            "-vvv",
            "--dry-run",
            "--exodus-conf",
            "/path/to/my-conf",
        ],
        [
            "exodus-rsync",
            "--exodus-publish",
            "497f6eca-6276-4993-bfeb-53cbbbba6f08",
            "--exclude",
            ".nfs*",
            "--exclude",
            ".latest_rsync",
            "--exclude",
            ".lock",
            os.path.join(src, "kickstart-repo-s390x", "RAW"),
            "exodus:kickstart-repo-s390x",
            "-vvv",
            "--dry-run",
            "--exodus-conf",
            "/path/to/my-conf",
        ],
    ]

    entry_point(args)

    assert "Exodus push begins" in caplog.text
    assert "fake exodus-rsync output" in caplog.text
    assert "fake task info" in caplog.text
    assert "Exodus push is complete" in caplog.text

    assert mock_popen.call_count == 2
    for cmd in cmds:
        mock_popen.assert_any_call(
            cmd, stderr=-2, stdout=-1, universal_newlines=True
        )


@mock.patch(
    "sys.argv",
    [
        "",
        "--debug",
        "--verbose",
        "staged:%s" % os.path.join(TEST_DATA, "source-2"),
    ],
)
@mock.patch("pubtools.exodus._tasks.push.subprocess.Popen")
def test_exodus_push_subprocess_error(mock_popen, successful_gw_task, caplog):
    mock_popen.return_value.stdout = io.StringIO(
        u("fake exodus-rsync output\nfake task info\n")
    )
    mock_popen.return_value.wait.return_value = 1

    caplog.set_level(logging.DEBUG, "pubtools-exodus")
    cmd = [
        "exodus-rsync",
        "--exodus-publish",
        "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "--exclude",
        ".nfs*",
        "--exclude",
        ".latest_rsync",
        "--exclude",
        ".lock",
        os.path.join(TEST_DATA, "source-2", "origin", "RAW"),
        "exodus:origin",
        "-v",
    ]

    with pytest.raises(RuntimeError) as exc_info:
        entry_point()
        assert exc_info.value == "Exodus push failed"

    assert "Exodus push begins" in caplog.text
    assert "fake exodus-rsync output" in caplog.text
    assert "fake task info" in caplog.text
    assert "Exodus push is complete" not in caplog.text
    mock_popen.assert_called_with(
        cmd, stderr=-2, stdout=-1, universal_newlines=True
    )


@mock.patch(
    "sys.argv",
    [
        "",
        "--debug",
        "--verbose",
        "test:%s" % os.path.join(TEST_DATA, "source-2"),
    ],
)
@mock.patch("pubtools.exodus._tasks.push.subprocess.Popen")
def test_exodus_push_unexpected_push_item(
    mock_popen, successful_gw_task, caplog
):
    mock_popen.return_value.wait.return_value = 1
    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    Source.register_backend("test", lambda: [PushItem(name="test")])

    entry_point()

    assert "Unexpected push item" in caplog.text
    mock_popen.assert_not_called()
