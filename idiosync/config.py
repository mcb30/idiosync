"""Configuration files"""

from abc import abstractmethod
from typing import ClassVar, Type
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


class DatabaseConfig(Config):
    """A database configuration"""

    def __init__(self, plugin, params):
        self.plugin = plugin
        self.params = params

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.plugin,
                               self.params)

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


DatabaseConfigType = Type[DatabaseConfig]
SynchronizerType = Type[Synchronizer]


class SynchronizerConfig(Config):
    """A database synchronizer configuration"""

    DatabaseConfig: ClassVar[DatabaseConfigType] = DatabaseConfig
    Synchronizer: ClassVar[SynchronizerType] = Synchronizer

    def __init__(self, src, dst):
        self.src = src
        self.dst = dst

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.src, self.dst)

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
