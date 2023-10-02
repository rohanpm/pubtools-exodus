import logging
import os
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

        This implementation adds to each config the necessary arguments
        to attach this repository's publish task to an exodus-gw publish.

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

        # 2023-10: by default, the pulp hook should always use phase1 commit.
        # But since the functionality is relatively new, this is provided as an
        # escape hatch in case it would need to be disabled in some environments
        # for unanticipated reasons.
        #
        # Consider deleting this conditional once the functionality is proven
        # in production.
        if os.getenv("EXODUS_PULP_HOOK_PHASE1_COMMIT", "1") == "1":
            args.append("--exodus-commit=phase1")

        return attr.evolve(options, rsync_extra_args=args)

    @property
    def exodus_enabled(self):
        # If this hook-specific env var is set, then it solely determines
        # whether the hook is enabled.
        enabled = os.getenv("EXODUS_PULP_HOOK_ENABLED")
        if enabled is not None:
            return enabled.lower() in ["true", "t", "1", "yes", "y"]

        # Otherwise, we let super decide, which will check a more generic env var.
        return super().exodus_enabled

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
