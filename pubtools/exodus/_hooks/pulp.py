import json
import logging
import sys
from threading import Lock

import attr
from pubtools.pluggy import hookimpl, pm  # pylint: disable=wrong-import-order
from six.moves.urllib.parse import urljoin

from ..gateway import ExodusGatewaySession

LOG = logging.getLogger("pubtools-exodus")

# pylint: disable=unused-argument


class ExodusPulpHandler(ExodusGatewaySession):
    def __init__(self):
        super(ExodusPulpHandler, self).__init__()

        self.lock = Lock()

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

        if not self.exodus_enabled:
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

        if not self.exodus_enabled:
            return

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
