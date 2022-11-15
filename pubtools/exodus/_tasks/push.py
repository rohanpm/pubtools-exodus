import logging
import os
import subprocess

import attr
from pushsource import Source

from pubtools.exodus.task import ExodusTask

LOG = logging.getLogger("pubtools-exodus")
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s"


class ExodusPushTask(ExodusTask):
    """Push a directory to the Exodus CDN"""

    def add_args(self):
        super(ExodusPushTask, self).add_args()

        self.parser.add_argument(
            "source",
            help=(
                """Source(s) of content to be pushed (e.g., 'staged:/path/to/staging/root')."""
            ),
        )

    @property
    def push_items(self):
        with Source.get(self.args.source) as source:
            for item in source:
                if item.src and len(item.dest) == 1:
                    # If the source directory passed to rsync does not end in a trailing
                    # slash ("/"), rsync will publish the entire directory, not just the
                    # contents of the directory.
                    #
                    # For example, "rsync ./example/rhel-8-for-x86_64-baseos-kickstart__7_DOT_4/RAW
                    # exodus:rhel-8-for-x86_64-baseos-kickstart__8_DOT_4" would
                    # publish to "/content/dist/rhel8/8.4/x86_64/baseos/kickstart/RAW",
                    # whereas "rsync ./example/rhel-8-for-x86_64-baseos-kickstart__8_DOT_4/RAW/
                    # exodus:rhel-8-for-x86_64-baseos-kickstart__8_DOT_4" would publish to
                    # "/content/dist/rhel8/8.4/x86_64/baseos/kickstart".
                    #
                    # See https://linux.die.net/man/1/rsync for more details.
                    item_src = item.src
                    if os.path.isdir(item.src) and not item.src.endswith("/"):
                        item_src = "%s/" % item.src
                    yield attr.evolve(item, src=item_src)
                else:
                    LOG.warning("Unexpected push item type: %s", item)

    def run(self):
        LOG.debug("Exodus push begins")

        publish = self.new_publish()
        publish_id = str(publish.get("id"))
        LOG.info("Publish ID: %s", publish_id)

        for item in self.push_items:
            LOG.debug("Processing %s", item)
            cmd = [
                "exodus-rsync",
                "--exodus-publish",
                publish_id,
                "--exclude",
                ".nfs*",
                "--exclude",
                ".latest_rsync",
                "--exclude",
                ".lock",
                item.src,
                "exodus:%s" % item.dest[0],
            ]
            if self.args.verbose:
                cmd.append("-" + "v" * self.args.verbose)
            if self.extra_args:
                cmd.extend(self.extra_args)

            LOG.info(" ".join(cmd))

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            for line in iter(proc.stdout.readline, ""):
                LOG.info(line.strip())

            ret = proc.wait()
            if ret != 0:
                raise RuntimeError("Exodus push failed")

        self.commit_publish(publish)

        LOG.info("Exodus push is complete")


def entry_point(args=None):
    task = ExodusPushTask(args)
    task.main()


def doc_parser():
    return ExodusPushTask().parser
