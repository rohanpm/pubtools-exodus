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
            "--source",
            help="Local path to a file or directory for sync to the exodus CDN",
        )
        self.parser.add_argument(
            "--dest",
            help="Remote destination for sync",
        )

    def run(self):
        LOG.debug("Exodus push begins")

        src = self.args.source
        dest = (
            self.args.dest
            if ":" in self.args.dest
            else "exodus:%s" % self.args.dest
        )

        cmd = [
            "exodus-rsync",
            src,
            dest,
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

        LOG.info("Exodus push is complete")


def entry_point():
    ExodusPushTask().main()
