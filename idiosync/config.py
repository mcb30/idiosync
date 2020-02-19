"""Configuration files"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Mapping, Type
import yaml
from .plugins import plugins
from .sync import Synchronizer


class ConfigError(Exception):
    """Configuration error"""

    def __str__(self):
        return "Configuration error: %s" % self.args


class Config:
    """A configuration subtree"""

    @classmethod
    @abstractmethod
    def parse(cls, config):
        """Parse configuration"""

    @classmethod
    def load(cls, filename):
        """Load configuration from YAML file"""
        with open(filename, 'r') as f:
            config = yaml.safe_load(f)
            try:
                return cls.parse(config)
            except ConfigError as e:
                raise ConfigError("In file '%s': %s" % (filename,
                                                        *e.args)) from e


@dataclass
class DatabaseConfig(Config):
    """A database configuration"""

    plugin: str
    params: Mapping

    @classmethod
    def parse(cls, config):
        """Parse configuration"""
        if 'plugin' not in config:
            raise ConfigError("Missing declaration 'plugin'")
        params = dict(config)
        plugin = params.pop('plugin')
        return cls(plugin, params)

    @property
    def database(self):
        """Configured database"""
        return plugins[self.plugin](**self.params)


DatabaseConfig_ = DatabaseConfig
Synchronizer_ = Synchronizer


@dataclass
class SynchronizerConfig(Config):
    """A database synchronizer configuration"""

    src: DatabaseConfig_
    dst: DatabaseConfig_

    DatabaseConfig: ClassVar[Type[DatabaseConfig_]] = DatabaseConfig
    Synchronizer: ClassVar[Type[Synchronizer_]] = Synchronizer

    @classmethod
    def parse(cls, config):
        """Parse configuration"""
        db = {}
        for k in ('source', 'destination'):
            if k not in config:
                raise ConfigError("Missing section '%s'" % k)
            try:
                db[k] = cls.DatabaseConfig.parse(config[k])
            except ConfigError as e:
                raise ConfigError("In section '%s': %s'" % (k, *e.args)) from e
        return cls(db['source'], db['destination'])

    @property
    def synchronizer(self):
        """Configured synchronizer"""
        return self.Synchronizer(self.src.database, self.dst.database)
