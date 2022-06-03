import logging
import subprocess

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
                    yield item
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
            for line in proc.stdout:
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
