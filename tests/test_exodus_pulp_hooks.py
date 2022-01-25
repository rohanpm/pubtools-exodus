import json
import logging
import os

import mock
import pytest
from pubtools.pluggy import pm, task_context
from requests.exceptions import HTTPError
from six.moves.urllib.parse import urljoin

from .conftest import FakePublishOptions


@mock.patch.dict(
    os.environ,
    {
        "EXODUS_ENABLED": "True",
        "EXODUS_GW_URL": "https://exodus-gw.example.com",
        "EXODUS_GW_ENV": "test",
        "EXODUS_GW_CERT": "path/to/ex.crt",
        "EXODUS_GW_KEY": "path/to/ex.key",
    },
)
def test_exodus_pulp_typical(requests_mock, caplog):
    url = os.getenv("EXODUS_GW_URL")
    env = os.getenv("EXODUS_GW_ENV")

    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    auth_resp = {
        "client": {
            "roles": [],
            "authenticated": False,
            "serviceAccountId": "testapp",
        },
        "user": {
            "roles": ["publisher"],
            "authenticated": True,
            "internalUsername": "tester",
        },
    }
    auth_url = urljoin(url, "/whoami")
    requests_mock.get(auth_url, json=auth_resp, status_code=200)

    publish_resp = {
        "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "env": "test",
        "links": {
            "self": "/test/publish/497f6eca-6276-4993-bfeb-53cbbbba6f08",
            "commit": "/test/publish/497f6eca-6276-4993-bfeb-53cbbbba6f08/commit",
        },
        "items": [],
    }
    publish_url = os.path.join(url, env, "publish")
    requests_mock.post(publish_url, json=publish_resp, status_code=200)

    commit_resp = {
        "id": "9187ec3d-ba51-4a3b-9298-e534b0869350",
        "publish_id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "state": "COMPLETE",
        "updated": "2022-01-18 18:16:52.000000+00:00",
        "links": {"self": "/task/9187ec3d-ba51-4a3b-9298-e534b0869350"},
    }
    commit_url = os.path.join(url, publish_resp["links"]["commit"])
    requests_mock.post(commit_url, json=commit_resp, status_code=200)

    task_url = os.path.join(url, commit_resp["links"]["self"])
    requests_mock.get(task_url, json=commit_resp, status_code=200)

    # Simulate task start
    with task_context():
        # Simulate repo publish; call prep-publish hook
        hook_rets = pm.hook.pulp_repository_pre_publish(
            repository=None,
            options=FakePublishOptions(rsync_extra_args=["--existing-arg"]),
        )
        hook_rets = [ret for ret in hook_rets if ret is not None]

        assert (
            "authenticated with exodus-gw at %s as user tester (roles: ['publisher'])"
            % url
            in caplog.text
        )
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
            % json.dumps(commit_resp, sort_keys=True)
            in caplog.text
        )


@mock.patch.dict(
    os.environ,
    {
        "EXODUS_ENABLED": "True",
        "EXODUS_GW_URL": "https://exodus-gw.example.com",
        "EXODUS_GW_ENV": "test",
    },
)
def test_exodus_pulp_no_auth(requests_mock, caplog):
    url = os.getenv("EXODUS_GW_URL")
    env = os.getenv("EXODUS_GW_ENV")

    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    auth_resp = {
        "client": {
            "roles": [],
            "authenticated": False,
            "serviceAccountId": "testapp",
        },
        "user": {
            "roles": [],
            "authenticated": False,
            "internalUsername": "tester",
        },
    }
    auth_url = urljoin(os.getenv("EXODUS_GW_URL"), "/whoami")
    requests_mock.get(auth_url, json=auth_resp, status_code=200)

    publish_url = os.path.join(url, env, "publish")
    requests_mock.post(
        publish_url, json={"detail": "Not Found"}, status_code=404
    )

    with task_context():
        with pytest.raises(HTTPError) as exc_info:
            pm.hook.pulp_repository_pre_publish(
                repository=None, options=FakePublishOptions()
            )

        assert "exodus-gw cert not found" in caplog.text
        assert "exodus-gw key not found" in caplog.text
        assert "not authenticated with exodus-gw at %s" % url in caplog.text
        assert (
            str(exc_info.value)
            == "404 Client Error: None for url: https://exodus-gw.example.com/test/publish"
        )


@mock.patch.dict(
    os.environ,
    {
        "EXODUS_ENABLED": "True",
        "EXODUS_GW_URL": "https://exodus-gw.example.com",
        "EXODUS_GW_ENV": "test",
        "EXODUS_GW_CERT": "path/to/ex.crt",
        "EXODUS_GW_KEY": "path/to/ex.key",
    },
)
def test_exodus_pulp_commit_fail(requests_mock, caplog):
    url = os.getenv("EXODUS_GW_URL")
    env = os.getenv("EXODUS_GW_ENV")

    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    auth_resp = {
        "client": {
            "roles": [],
            "authenticated": False,
            "serviceAccountId": "testapp",
        },
        "user": {
            "roles": ["publisher"],
            "authenticated": True,
            "internalUsername": "tester",
        },
    }
    auth_url = urljoin(url, "/whoami")
    requests_mock.get(auth_url, json=auth_resp, status_code=200)

    publish_resp = {
        "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "env": "test",
        "links": {
            "self": "/test/publish/497f6eca-6276-4993-bfeb-53cbbbba6f08",
            "commit": "/test/publish/497f6eca-6276-4993-bfeb-53cbbbba6f08/commit",
        },
        "items": [],
    }
    publish_url = os.path.join(url, env, "publish")
    requests_mock.post(publish_url, json=publish_resp, status_code=200)

    commit_resp = {
        "id": "9187ec3d-ba51-4a3b-9298-e534b0869350",
        "publish_id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "state": "IN_PROGRESS",
        "updated": "2022-01-18 18:16:52.000000+00:00",
        "links": {"self": "/task/9187ec3d-ba51-4a3b-9298-e534b0869350"},
    }
    commit_url = os.path.join(url, publish_resp["links"]["commit"])
    requests_mock.post(commit_url, json=commit_resp, status_code=200)

    task_resp = {
        "id": "9187ec3d-ba51-4a3b-9298-e534b0869350",
        "publish_id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "state": "FAILED",
        "updated": "2022-01-18 18:16:53.000000+00:00",
        "links": {"self": "/task/9187ec3d-ba51-4a3b-9298-e534b0869350"},
    }
    task_url = os.path.join(url, commit_resp["links"]["self"])
    requests_mock.get(task_url, json=task_resp, status_code=200)

    with task_context():
        pm.hook.pulp_repository_pre_publish(
            repository=None,
            options=FakePublishOptions(),
        )

        with pytest.raises(RuntimeError) as exc_info:
            pm.hook.task_pulp_flush()

        assert str(exc_info.value) == "exodus-gw commit %s to %s failed" % (
            task_resp["id"],
            url,
        )


@mock.patch.dict(
    os.environ,
    {
        "EXODUS_ENABLED": "True",
        "EXODUS_GW_URL": "https://exodus-gw.example.com",
        "EXODUS_GW_ENV": "test",
        "EXODUS_GW_CERT": "path/to/ex.crt",
        "EXODUS_GW_KEY": "path/to/ex.key",
        "EXODUS_GW_TIMEOUT": "1",
        "EXODUS_GW_WAIT": "1",
    },
)
def test_exodus_pulp_commit_timeout(requests_mock, caplog):
    url = os.getenv("EXODUS_GW_URL")
    env = os.getenv("EXODUS_GW_ENV")

    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    auth_resp = {
        "client": {
            "roles": [],
            "authenticated": False,
            "serviceAccountId": "testapp",
        },
        "user": {
            "roles": ["publisher"],
            "authenticated": True,
            "internalUsername": "tester",
        },
    }
    auth_url = urljoin(url, "/whoami")
    requests_mock.get(auth_url, json=auth_resp, status_code=200)

    publish_resp = {
        "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "env": "test",
        "links": {
            "self": "/test/publish/497f6eca-6276-4993-bfeb-53cbbbba6f08",
            "commit": "/test/publish/497f6eca-6276-4993-bfeb-53cbbbba6f08/commit",
        },
        "items": [],
    }
    publish_url = os.path.join(url, env, "publish")
    requests_mock.post(publish_url, json=publish_resp, status_code=200)

    commit_resp = {
        "id": "9187ec3d-ba51-4a3b-9298-e534b0869350",
        "publish_id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "state": "IN_PROGRESS",
        "updated": "2022-01-18 18:16:52.000000+00:00",
        "links": {"self": "/task/9187ec3d-ba51-4a3b-9298-e534b0869350"},
    }
    commit_url = os.path.join(url, publish_resp["links"]["commit"])
    requests_mock.post(commit_url, json=commit_resp, status_code=200)

    task_url = os.path.join(url, commit_resp["links"]["self"])
    requests_mock.get(task_url, json=commit_resp, status_code=200)

    with task_context():
        pm.hook.pulp_repository_pre_publish(
            repository=None,
            options=FakePublishOptions(),
        )

        with pytest.raises(RuntimeError) as exc_info:
            pm.hook.task_pulp_flush()

        assert str(
            exc_info.value
        ) == "Polling for exodus-gw commit %s to %s timed out" % (
            commit_resp["id"],
            url,
        )


@mock.patch.dict(
    os.environ,
    {
        "EXODUS_ENABLED": "True",
        "EXODUS_GW_URL": "https://exodus-gw.example.com",
    },
)
def test_exodus_pulp_bad_response(requests_mock):
    auth_url = urljoin(os.getenv("EXODUS_GW_URL"), "/whoami")
    requests_mock.get(auth_url, json=None, status_code=503)

    with task_context():
        with pytest.raises(HTTPError) as exc_info:
            pm.hook.pulp_repository_pre_publish(repository=None, options={})

        assert (
            str(exc_info.value)
            == "503 Server Error: None for url: https://exodus-gw.example.com/whoami"
        )


@mock.patch.dict(os.environ, {"EXODUS_ENABLED": "True"})
def test_exodus_pulp_no_publish(caplog):
    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    with task_context():
        pm.hook.task_pulp_flush()

        assert "no exodus-gw publish to commit" in caplog.text


@mock.patch.dict(os.environ, {"EXODUS_ENABLED": "False"})
def test_exodus_pulp_disabled(caplog):
    caplog.set_level(logging.DEBUG, "pubtools-exodus")

    with task_context():
        # With Exodus disabled, this should be a no-op.
        pm.hook.pulp_repository_pre_publish(repository=None, options={})

    assert caplog.text == ""
