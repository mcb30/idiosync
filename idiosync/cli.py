"""Command line interface"""

from abc import ABC, abstractmethod
import argparse
from contextlib import nullcontext
import logging
from .config import Config, DatabaseConfig, SynchronizerConfig


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


class ConfigCommand(Command):
    """An executable command utilising a configuration file"""
    # pylint: disable=abstract-method

    Config = Config

    def __init__(self, argv=None):
        super().__init__(argv)
        self.config = self.Config.load(self.args.config)

    @classmethod
    def parser(cls, **kwargs):
        """Construct argument parser"""
        parser = super().parser(**kwargs)
        parser.add_argument('config', help="Configuration file")
        return parser


class WatchCommand(Command):
    """An executable command for watching a database"""
    # pylint: disable=abstract-method

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
        return parser


class SynchronizeCommand(ConfigCommand, WatchCommand):
    """Synchronize user database"""

    Config = SynchronizerConfig

    @classmethod
    def parser(cls, **kwargs):
        """Construct argument parser"""
        parser = super().parser(**kwargs)
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
        return parser

    def execute(self):
        """Execute command"""
        self.config.synchronizer.sync(persist=self.args.persist,
                                      strict=self.args.strict,
                                      delete=self.args.delete)


class TraceCommand(ConfigCommand, WatchCommand):
    """Trace user database changes"""

    Config = DatabaseConfig

    @classmethod
    def parser(cls, **kwargs):
        """Construct argument parser"""
        parser = super().parser(**kwargs)
        parser.add_argument('--output', '-o', help="Output file")
        parser.add_argument('--cookie', '-c', help="Cookie file")
        return parser

    def execute(self):
        """Execute command"""
        with (open(self.args.output, 'wt') if self.args.output else
              nullcontext()) as fh:
            with (open(self.args.cookie, 'a+t') if self.args.cookie else
                  nullcontext()) as cookiefh:
                self.config.database.trace(fh=fh, cookiefh=cookiefh,
                                           persist=self.args.persist)
