import logging
import subprocess

from pubtools.exodus.task import ExodusTask

LOG = logging.getLogger("pubtools-exodus")
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s"


class ExodusPushTask(ExodusTask):
    """Push a directory to the Exodus CDN"""

    def add_args(self):
        super(ExodusPushTask, self).add_args()

        self.parser.add_argument(
            "sync",
            nargs="+",
            help=(
                """A comma-separated pair of paths to sync: SRC,DEST.\n"""
                """Where SRC is a local path to a file or directory and DEST\n"""
                """is the remote destination for sync."""
            ),
        )

    def run(self):
        LOG.debug("Exodus push begins")

        publish = self.new_publish()
        publish_id = str(publish.get("id"))
        LOG.info("Publish ID: %s", publish_id)

        for item in self.args.sync:
            LOG.debug("Processing %s", item)
            items = item.split(",")
            src, dest = items[0].strip(), items[1].strip()
            dest = dest if ":" in dest else "exodus:%s" % dest

            cmd = ["exodus-rsync", "--exodus-publish", publish_id, src, dest]
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
            for line in proc.stdout:
                LOG.info(line.strip())

            ret = proc.wait()
            if ret != 0:
                raise RuntimeError("Exodus push failed")

        commit_task = self.commit_publish(publish)
        self.poll_commit_completion(commit_task)

        LOG.info("Exodus push is complete")


def entry_point(args=None):
    task = ExodusPushTask(args)
    task.main()
