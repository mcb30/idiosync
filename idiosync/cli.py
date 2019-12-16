"""Command line interface"""

from abc import ABC, abstractmethod
import argparse
import logging
from .config import SynchronizerConfig


class Command(ABC):
    """An executable command"""

    loglevels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]

    def __init__(self, argv=None):
        self.args = self.parser().parse_args(argv)
        self.verbosity = (self.loglevels.index(logging.INFO) +
                          self.args.verbose - self.args.quiet)
        logging.basicConfig(level=self.loglevel)

    @classmethod
    def parser(cls, **kwargs):
        """Construct argument parser"""
        parser = argparse.ArgumentParser(description=cls.__doc__, **kwargs)
        parser.add_argument('--verbose', '-v', action='count', default=0)
        parser.add_argument('--quiet', '-q', action='count', default=0)
        return parser

    @property
    def loglevel(self):
        """Log level"""
        return (self.loglevels[self.verbosity]
                if self.verbosity < len(self.loglevels) else logging.NOTSET)

    @abstractmethod
    def execute(self):
        """Execute command"""

    @classmethod
    def main(cls):
        """Execute command (as main entry point)"""
        cls().execute()


class SynchronizeCommand(Command):
    """Synchronize user database"""

    Config = SynchronizerConfig

    def __init__(self, argv=None):
        super().__init__(argv)
        self.config = self.Config.load(self.args.config)

    @classmethod
    def parser(cls, **kwargs):
        """Construct argument parser"""
        parser = super().parser(**kwargs)
        persist = parser.add_mutually_exclusive_group()
        persist.add_argument(
            '--persist', action='store_true', default=True,
            help="Refresh and persist (default)",
        )
        persist.add_argument(
            '--no-persist', action='store_false', dest='persist',
            help="Refresh only",
        )
        strict = parser.add_mutually_exclusive_group()
        strict.add_argument(
            '--strict', action='store_true',
            help="Identify matching entries only by permanent UUID",
        )
        strict.add_argument(
            '--no-strict', action='store_false', dest='strict', default=False,
            help="Guess matching entries where possible (default)",
        )
        delete = parser.add_mutually_exclusive_group()
        delete.add_argument(
            '--delete', action='store_true',
            help="Allow deletion of entries",
        )
        delete.add_argument(
            '--no-delete', action='store_false', dest='delete', default=False,
            help="Disable deleted entries (default)",
        )
        parser.add_argument('config', help="Configuration file")
        return parser

    def execute(self):
        """Execute command"""
        self.config.synchronizer.sync(persist=self.args.persist,
                                      strict=self.args.strict,
                                      delete=self.args.delete)
