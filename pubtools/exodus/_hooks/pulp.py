import json
import logging
import os
import sys
import time
from threading import Lock

import attr
import requests
from monotonic import monotonic
from pubtools.pluggy import hookimpl, pm  # pylint: disable=wrong-import-order
from requests.packages.urllib3.util.retry import (  # pylint: disable=import-error
    Retry,
)
from six.moves.urllib.parse import urljoin

LOG = logging.getLogger("pubtools-exodus")

# pylint: disable=unused-argument


class ExodusPulpHandler:  # pylint: disable=too-many-instance-attributes
    def __init__(self):
        # These variables are set only through environment variables
        # expected on all applicable hosts.
        self.gw_url = os.getenv("EXODUS_GW_URL")
        self.gw_env = os.getenv("EXODUS_GW_ENV")
        self.gw_crt = os.getenv("EXODUS_GW_CERT")
        self.gw_key = os.getenv("EXODUS_GW_KEY")

        # These defaults are not advertised or expected but can be controlled
        # by environment variables when needed (e.g., testing).
        self.retries = int(os.getenv("EXODUS_GW_RETRIES") or "5")
        self.timeout = int(os.getenv("EXODUS_GW_TIMEOUT") or "900")
        self.wait = int(os.getenv("EXODUS_GW_WAIT") or "5")

        self.lock = Lock()
        self.session = None
        self.publish = None

    def exodus_enabled(self):
        enable_vals = ["true", "t", "1", "yes", "y"]
        return os.getenv("EXODUS_ENABLED", "False").lower() in enable_vals

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

            LOG.error("unsuccessful response from exodus-gw: %s", body)
            raise

    def do_request(self, **kwargs):
        if not self.session:
            self.session = self.new_session()

        resp = self.session.request(**kwargs)
        self.unpack_response(resp)
        return resp

    def check_cert(self):
        """Issue request to exodus-gw to identify permissions."""

        for key, val in {"cert": self.gw_crt, "key": self.gw_key}.items():
            if not val:
                LOG.debug(
                    "exodus-gw %s not found, authentication may fail", key
                )

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
                    "authenticated with exodus-gw at %s as %s %s (roles: %s)",
                    self.gw_url,
                    user_type,
                    typed_ctx[ident],
                    roles,
                )
                break
        else:
            LOG.debug("not authenticated with exodus-gw at %s", self.gw_url)

    def new_publish(self):
        """Issue request to exodus-gw to create a new publish."""
        self.check_cert()

        publish_url = os.path.join(self.gw_url, self.gw_env, "publish")
        resp = self.do_request(method="POST", url=publish_url)
        return resp.json()

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
                LOG.info("%s complete", msg)
                return task
            if task["state"] == "FAILED":
                raise RuntimeError("%s failed" % msg)

            time.sleep(self.wait)

        raise RuntimeError("Polling for %s timed out" % msg)

    @hookimpl
    def pulp_repository_pre_publish(self, repository, options):
        """Invoked as the first step in publishing a Pulp repository.

        This implementation adds to each config the --exodus-publish argument,
        attaching the repository to an exodus-gw publish.

        Args:
            repository (:class:`~pubtools.pulplib.Repository`):
                The repository to be published.
            options (:class:`~pubtools.pulplib.PublishOptions`):
                The options to use in publishing.
        Returns:
            options (:class:`~pubtools.pulplib.PublishOptions`):
                The adjusted options used for this publish.
        """

        if not self.exodus_enabled():
            return None

        with self.lock:
            if not self.publish:
                self.publish = self.new_publish()
                LOG.debug("created exodus-gw publish %s", self.publish["id"])

        args = (
            list(options.rsync_extra_args) if options.rsync_extra_args else []
        )
        args.append("--exodus-publish=%s" % self.publish["id"])
        return attr.evolve(options, rsync_extra_args=args)

    @hookimpl
    def task_pulp_flush(self):
        """Invoked during task execution after successful completion of all
        Pulp publishes.

        This implementation commits the active exodus-gw publish, making
        the content visible on the target CDN environment.
        """

        if not self.publish:
            LOG.debug("no exodus-gw publish to commit")
            return

        commit_url = urljoin(self.gw_url, self.publish["links"]["commit"])
        resp = self.do_request(method="POST", url=commit_url)
        commit = resp.json()

        task = self.poll_commit_completion(commit)
        LOG.info(
            "committed exodus-gw publish: %s", json.dumps(task, sort_keys=True)
        )

    @hookimpl
    def task_stop(self):
        pm.unregister(self)


@hookimpl
def task_start():
    pm.register(ExodusPulpHandler())


pm.register(sys.modules[__name__])
