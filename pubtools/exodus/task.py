import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from pubtools.pluggy import task_context

from .gateway import ExodusGatewaySession

LOG = logging.getLogger("pubtools-exodus")
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s"


class ExodusTask(ExodusGatewaySession):
    """Base class for Exodus tasks"""

    def __init__(self, args=None):
        super(ExodusTask, self).__init__(exodus_enabled=True)

        self._args = None
        self._extra_args = None
        self._override_args = args

        self.parser = ArgumentParser(
            formatter_class=RawDescriptionHelpFormatter
        )
        self._basic_args()
        self.add_args()

    @property
    def args(self):
        """Parsed args from the cli
        Return the args if available from previous parse
        else parse with defined options and return the args
        """
        if not self._args:
            self._args, _ = self.parser.parse_known_args(self._override_args)
        return self._args

    @property
    def extra_args(self):
        """Remaining args from the cli
        Return the remaining args from the previous parse,
        else parse and return the remaining args
        """
        if not self._extra_args:
            _, self._extra_args = self.parser.parse_known_args(
                self._override_args
            )
        return self._extra_args

    def _basic_args(self):
        # minimum args required for a CLI task
        self.parser.add_argument(
            "--debug",
            "-d",
            action="store_true",
            help=("Show debug logs"),
        )
        self.parser.add_argument(
            "--verbose",
            "-v",
            action="count",
            default=0,
            help=("Increase verbosity"),
        )

    def add_args(self):
        """Add parser options/arguments for a task
        e.g. self.parser.add_argument("option", help="help text")
        """
        # Calling super add_args if it exists allows this class and
        # Service classes to be inherited in either order without breaking.
        from_super = getattr(super(ExodusTask, self), "add_args", lambda: None)
        from_super()

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
        if self.args.debug:
            logging.getLogger("pubtools-exodus").setLevel(logging.DEBUG)

    def run(self):
        """Implement a specific task"""

        raise NotImplementedError()

    def main(self):
        """Main method called by the entrypoint of the task."""

        with task_context():
            # setup the logging as required
            self._setup_logging()

            self.run()
            return 0
