import logging
import os
from urllib.parse import urljoin

import mock
import pytest
from requests.exceptions import HTTPError

from pubtools.exodus.gateway import ExodusGatewaySession


@pytest.mark.parametrize(
    "env_vars",
    [
        (
            {"key": "EXODUS_ENABLED", "val": "true"},
            {"key": "EXODUS_GW_CERT", "val": "/fake/cert"},
            {"key": "EXODUS_GW_KEY", "val": "/fake/key"},
            {"key": "EXODUS_GW_ENV", "val": "test"},
            {"key": "EXODUS_GW_URL", "val": ""},
        ),
        (
            {"key": "EXODUS_ENABLED", "val": "true"},
            {
                "key": "EXODUS_GW_URL",
                "val": "https://exodus-gw.test.redhat.com",
            },
            {"key": "EXODUS_GW_KEY", "val": "/fake/key"},
            {"key": "EXODUS_GW_ENV", "val": "test"},
            {"key": "EXODUS_GW_CERT", "val": ""},
        ),
        (
            {"key": "EXODUS_ENABLED", "val": "true"},
            {
                "key": "EXODUS_GW_URL",
                "val": "https://exodus-gw.test.redhat.com",
            },
            {"key": "EXODUS_GW_CERT", "val": "/fake/cert"},
            {"key": "EXODUS_GW_ENV", "val": "test"},
            {"key": "EXODUS_GW_KEY", "val": ""},
        ),
        (
            {"key": "EXODUS_ENABLED", "val": "true"},
            {
                "key": "EXODUS_GW_URL",
                "val": "https://exodus-gw.test.redhat.com",
            },
            {"key": "EXODUS_GW_CERT", "val": "/fake/cert"},
            {"key": "EXODUS_GW_ENV", "val": ""},
            {"key": "EXODUS_GW_KEY", "val": "/fake/key"},
        ),
    ],
)
def test_missing_env_vars(monkeypatch, env_vars):
    for env_var in env_vars:
        monkeypatch.setenv(env_var["key"], env_var["val"])
        if not env_var["val"]:
            missing_key = env_var["key"]
    with pytest.raises(RuntimeError) as exc_info:
        ExodusGatewaySession().new_publish()
        assert (
            str(exc_info.value)
            == "Environment variable '%s' is not set" % missing_key
        )


def test_exodus_gateway_bad_response(requests_mock, patch_env_vars):
    auth_url = urljoin(os.getenv("EXODUS_GW_URL"), "/whoami")
    requests_mock.get(auth_url, json=None, status_code=503)

    with pytest.raises(HTTPError) as exc_info:
        ExodusGatewaySession().new_publish()

    assert (
        str(exc_info.value)
        == "503 Server Error: None for url: https://exodus-gw.test.redhat.com/whoami"
    )


@mock.patch.dict(
    os.environ,
    {
        "EXODUS_ENABLED": "True",
        "EXODUS_GW_URL": "https://exodus-gw.test.redhat.com",
        "EXODUS_GW_ENV": "test",
        "EXODUS_GW_CERT": "path/to/ex.crt",
        "EXODUS_GW_KEY": "path/to/ex.key",
        "EXODUS_GW_TIMEOUT": "1",
        "EXODUS_GW_WAIT": "1",
    },
)
def test_exodus_gateway_commit_timeout(requests_mock, caplog):
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

    requests_mock.post(publish_resp["links"]["self"], status_code=200)

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

    with pytest.raises(RuntimeError) as exc_info:
        gw_conn = ExodusGatewaySession()
        gw_conn.publish = gw_conn.new_publish()
        gw_conn.commit_publish(gw_conn.publish)

    assert (
        "Authenticated with exodus-gw at %s as user tester (roles: ['publisher'])"
        % url
        in caplog.text
    )
    assert str(
        exc_info.value
    ) == "Polling for exodus-gw commit %s to %s timed out" % (
        commit_resp["id"],
        url,
    )


def test_exodus_pulp_commit_fail(requests_mock, caplog, patch_env_vars):
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

    with pytest.raises(RuntimeError) as exc_info:
        gw_conn = ExodusGatewaySession()
        gw_conn.publish = gw_conn.new_publish()
        gw_conn.commit_publish(gw_conn.publish)

    assert (
        "Authenticated with exodus-gw at %s as user tester (roles: ['publisher'])"
        % url
        in caplog.text
    )
    assert str(exc_info.value) == "exodus-gw commit %s to %s failed" % (
        task_resp["id"],
        url,
    )


def test_exodus_pulp_no_auth(requests_mock, caplog, patch_env_vars):
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

    with pytest.raises(HTTPError) as exc_info:
        gw_conn = ExodusGatewaySession()
        gw_conn.publish = gw_conn.new_publish()
        gw_conn.commit_publish(gw_conn.publish)

    assert "Not authenticated with exodus-gw at %s" % url in caplog.text
    assert (
        str(exc_info.value)
        == "404 Client Error: None for url: https://exodus-gw.test.redhat.com/test/publish"
    )
