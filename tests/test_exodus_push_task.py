import io
import logging

import mock
import pytest
from six import u

from pubtools.exodus._tasks.push import entry_point


@pytest.mark.parametrize(
    "sys_argv",
    [["", "--debug", "/path/to/my-source,/path/to/my-dest"]],
)
@mock.patch("pubtools.exodus._tasks.push.ExodusPushTask.run")
def test_exodus_push_entry_point(
    mock_run,
    patch_sys_argv,
    patch_env_vars,
):
    entry_point()
    assert mock_run.call_count == 1


@mock.patch("pubtools.exodus._tasks.push.subprocess.Popen")
def test_exodus_push_typical(mock_popen, successful_gw_task, caplog):
    mock_popen.return_value.stdout = io.StringIO(
        u("fake exodus-rsync output\nfake task info\n")
    )
    mock_popen.return_value.wait.return_value = 0

    args = [
        "--debug",
        "-vvv",
        "--dry-run",
        "/path/to/my-source,/path/to/my-dest",
        "/path/to/other-source,/path/to/other-dest",
        "--exodus-conf",
        "/path/to/my-conf",
    ]
    caplog.set_level(logging.DEBUG, "pubtools-exodus")
    cmds = [
        [
            "exodus-rsync",
            "--exodus-publish",
            "497f6eca-6276-4993-bfeb-53cbbbba6f08",
            "/path/to/my-source",
            "exodus:/path/to/my-dest",
            "-vvv",
            "--dry-run",
            "--exodus-conf",
            "/path/to/my-conf",
        ],
        [
            "exodus-rsync",
            "--exodus-publish",
            "497f6eca-6276-4993-bfeb-53cbbbba6f08",
            "/path/to/other-source",
            "exodus:/path/to/other-dest",
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


@pytest.mark.parametrize(
    "sys_argv",
    [
        [
            "",
            "--debug",
            "--verbose",
            "/path/to/my-source,/path/to/my-dest",
        ]
    ],
)
@mock.patch("pubtools.exodus._tasks.push.subprocess.Popen")
def test_exodus_push_subprocess_error(
    mock_popen, successful_gw_task, patch_sys_argv, caplog
):
    mock_popen.return_value.stdout = io.StringIO(
        u("fake exodus-rsync output\nfake task info\n")
    )
    mock_popen.return_value.wait.return_value = 1

    caplog.set_level(logging.DEBUG, "pubtools-exodus")
    cmd = [
        "exodus-rsync",
        "--exodus-publish",
        "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "/path/to/my-source",
        "exodus:/path/to/my-dest",
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
