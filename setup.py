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
    },
    test_suite='test',
)
