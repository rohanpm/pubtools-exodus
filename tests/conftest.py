import os
import sys

import attr
import pytest
import requests_mock
from frozenlist2 import frozenlist
from six.moves.urllib.parse import urljoin


def frozenlist_or_none_converter(obj, map_fn=(lambda x: x)):
    if obj is not None:
        return frozenlist(map_fn(obj))
    return None


@attr.s(kw_only=True, frozen=True)
class FakePublishOptions(object):
    """Options controlling a repository"""

    rsync_extra_args = attr.ib(
        default=None, type=list, converter=frozenlist_or_none_converter  # type: ignore
    )


@pytest.fixture
def patch_env_vars(monkeypatch, env_map=None):
    if not env_map:
        env_map = {
            "EXODUS_ENABLED": "true",
            "EXODUS_GW_URL": "https://exodus-gw.test.redhat.com",
            "EXODUS_GW_ENV": "test",
            "EXODUS_GW_CERT": "/path/test.crt",
            "EXODUS_GW_KEY": "/path/test.key",
        }
    for var in env_map.keys():
        monkeypatch.setenv(var, env_map[var])
    yield env_map


@pytest.fixture
def patch_sys_argv(sys_argv):
    old_argv = sys.argv
    sys.argv[:] = sys_argv
    yield
    sys.argv = old_argv


@pytest.fixture
def successful_gw_task(patch_env_vars, requests_mock):
    url = patch_env_vars["EXODUS_GW_URL"]
    env = patch_env_vars["EXODUS_GW_ENV"]
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
    yield {
        "auth": {"url": auth_url, "response": auth_resp},
        "publish": {"url": publish_url, "response": publish_resp},
        "commit": {"url": commit_url, "response": commit_resp},
        "task": {"url": task_url, "response": commit_resp},
    }
