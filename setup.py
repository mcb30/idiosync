#!/usr/bin/env python3

"""Setup script"""

import os
from setuptools import setup, find_packages

setup(
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=['test']),
    use_scm_version=True,
    setup_requires=[
        'setuptools_scm',
    ],
    install_requires=([
        'alembic',
        'pyasn1',
        'pyyaml',
        'setuptools',
        'sqlalchemy',
    ] + ([] if os.getenv('READTHEDOCS') else [
        'python-ldap',
    ])),
    entry_points={
        'console_scripts': [
            'idiosync=idiosync.cli:SynchronizeCommand.main',
            'idiotrace=idiosync.cli:TraceCommand.main',
        ],
        'idiosync.plugins': [
            'ldap=idiosync.ldap:LdapDatabase',
            'rfc2307=idiosync.rfc2307:Rfc2307Database',
            'freeipa=idiosync.freeipa:IpaDatabase',
            'mediawiki=idiosync.mediawiki:MediaWikiDatabase',
            'requesttracker=idiosync.requesttracker:RequestTrackerDatabase',
        ],
    },
    test_suite='test',
)
