"""Plugin registration"""

from pkg_resources import iter_entry_points

__all__ = [
    'plugins',
]

plugins = {ep.name: ep.load() for ep in iter_entry_points(__name__)}
