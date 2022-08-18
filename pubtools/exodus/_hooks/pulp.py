import logging
import sys
from threading import Lock

import attr
from pubtools.pluggy import hookimpl, pm  # pylint: disable=wrong-import-order

from ..gateway import ExodusGatewaySession

LOG = logging.getLogger("pubtools-exodus")

# pylint: disable=unused-argument


class ExodusPulpHandler(ExodusGatewaySession):
    def __init__(self):
        super(ExodusPulpHandler, self).__init__()

        self.lock = Lock()
        self.publish_committed = False

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

        with self.lock:
            if not self.publish:
                self.publish = self.new_publish()

        if not self.publish:
            return None

        args = (
            list(options.rsync_extra_args) if options.rsync_extra_args else []
        )
        args.append("--exodus-publish=%s" % self.publish["id"])
        return attr.evolve(options, rsync_extra_args=args)

    def ensure_publish_committed(self):
        """Commit the current publish, if and only if there is a current publish
        and it was not already committed.
        """
        if not self.publish:
            LOG.debug("No exodus-gw publish to commit")
            return

        if self.publish_committed:
            LOG.debug("Publish is already committed")
            return

        self.publish_committed = True
        self.commit_publish(self.publish)

    @hookimpl
    def task_pulp_flush(self):
        """Invoked during task execution after successful completion of all
        Pulp publishes.

        This implementation commits the active exodus-gw publish, making
        the content visible on the target CDN environment.
        """
        self.ensure_publish_committed()

    @hookimpl
    def task_stop(self, failed):
        pm.unregister(self)
        if not failed:
            # If a task is finishing up successfully and there's still an uncommitted
            # publish, make sure to commit it. This is not expected to do anything
            # if the commit happened earlier via task_pulp_flush.
            self.ensure_publish_committed()


@hookimpl
def task_start():
    pm.register(ExodusPulpHandler())


pm.register(sys.modules[__name__])
