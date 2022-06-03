import logging
import os
import time

import requests
from monotonic import monotonic
from requests.packages.urllib3.util.retry import (  # pylint: disable=import-error
    Retry,
)
from six.moves.urllib.parse import urljoin

LOG = logging.getLogger("pubtools-exodus")
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s"


class ExodusGatewaySession(
    object
):  # pylint: disable=too-many-instance-attributes
    """Base class for operations passing through exodus-gateway."""

    def __init__(self, exodus_enabled=None):
        super(ExodusGatewaySession, self).__init__()

        self.gw_env = None
        self.gw_url = None
        self.gw_crt = None
        self.gw_key = None

        self.session = None
        self.publish = None

        self._exodus_enabled = exodus_enabled

        # These defaults are not advertised or expected but can be controlled
        # by environment variables when needed (e.g., testing).
        self.retries = int(os.getenv("EXODUS_GW_RETRIES") or "5")
        self.timeout = int(os.getenv("EXODUS_GW_TIMEOUT") or "900")
        self.wait = int(os.getenv("EXODUS_GW_WAIT") or "5")

    def new_session(self):
        retry_strategy = Retry(
            total=int(self.retries),
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)

        out = requests.Session()
        out.cert = (self.gw_crt, self.gw_key)
        out.mount(self.gw_url, adapter)

        return out

    def unpack_response(self, response):
        """Raise if response was not successful.

        This is the same as response.raise_for_status(), merely wrapping it
        to ensure the body is logged when possible.
        """

        try:
            response.raise_for_status()
        except Exception as outer:
            try:
                body = response.json()
            except:
                raise outer

            LOG.error(
                "Unsuccessful response from exodus-gw: %s",
                body.get("detail") or body,
            )
            raise

    def do_request(self, **kwargs):
        if not self.session:
            self.session = self.new_session()

        resp = self.session.request(**kwargs)
        self.unpack_response(resp)
        return resp

    def check_cert(self):
        """Issue request to exodus-gw to identify permissions."""

        auth_url = urljoin(self.gw_url, "/whoami")
        resp = self.do_request(method="GET", url=auth_url)
        context = resp.json()

        for user_type, ident in (
            ("client", "serviceAccountId"),
            ("user", "internalUsername"),
        ):
            typed_ctx = context[user_type]
            if typed_ctx["authenticated"]:
                roles = [str(role) for role in typed_ctx["roles"]]
                LOG.debug(
                    "Authenticated with exodus-gw at %s as %s %s (roles: %s)",
                    self.gw_url,
                    user_type,
                    typed_ctx[ident],
                    roles,
                )
                break
        else:
            LOG.debug("Not authenticated with exodus-gw at %s", self.gw_url)

    def new_publish(self):
        """Issue request to exodus-gw to create a new publish."""

        if not self.exodus_enabled:
            return None

        self._populate_exodus_gw_vars()
        self.check_cert()

        publish_url = os.path.join(self.gw_url, self.gw_env, "publish")
        resp_json = self.do_request(method="POST", url=publish_url).json()

        LOG.info("Created exodus-gw publish %s", resp_json["id"])

        return resp_json

    def poll_commit_completion(self, commit):
        """Issues request(s) to exodus-gw for the commit's state, returning
        if/when the state is either "COMPLETE" or "FAILED".
        """

        timelimit = monotonic() + self.timeout

        msg = "exodus-gw commit %s to %s" % (commit["id"], self.gw_url)

        while monotonic() < timelimit:
            task_url = urljoin(self.gw_url, commit["links"]["self"])
            resp = self.do_request(method="GET", url=task_url)
            task = resp.json()

            if task["state"] == "COMPLETE":
                LOG.debug("%s complete", msg)
                return task
            if task["state"] == "FAILED":
                raise RuntimeError("%s failed" % msg)

            time.sleep(self.wait)

        raise RuntimeError("Polling for %s timed out" % msg)

    def commit_publish(self, publish):
        """Commits an exodus-gw publish, e.g.,
        https://exodus-gw.example.com/prod/publish/4e59c1a0/commit
        """

        LOG.info("Committing exodus-gw publish %s", publish["id"])

        commit_url = urljoin(self.gw_url, publish["links"]["commit"])
        resp = self.do_request(method="POST", url=commit_url)
        commit = resp.json()

        self.poll_commit_completion(commit)

        LOG.info("Committed exodus-gw publish %s", publish["id"])

    @property
    def exodus_enabled(self):
        if self._exodus_enabled is None:
            enable_vals = ["true", "t", "1", "yes", "y"]
            self._exodus_enabled = (
                os.getenv("EXODUS_ENABLED", "False").lower() in enable_vals
            )
        return self._exodus_enabled

    def _populate_exodus_gw_vars(self):
        """Populate exodus gateway details from environment variables. All exodus CDN transactions
        go through exodus gateway."""

        self.gw_env = os.getenv("EXODUS_GW_ENV")
        if not self.gw_env:
            raise RuntimeError(
                "Environment variable '%s' is not set" % "EXODUS_GW_ENV"
            )

        self.gw_url = os.getenv("EXODUS_GW_URL")
        if not self.gw_url:
            raise RuntimeError(
                "Environment variable '%s' is not set" % "EXODUS_GW_URL"
            )

        self.gw_crt = os.getenv("EXODUS_GW_CERT")
        if not self.gw_crt:
            raise RuntimeError(
                "Environment variable '%s' is not set" % "EXODUS_GW_CERT"
            )

        self.gw_key = os.getenv("EXODUS_GW_KEY")
        if not self.gw_key:
            raise RuntimeError(
                "Environment variable '%s' is not set" % "EXODUS_GW_KEY"
            )
