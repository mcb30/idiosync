#!/usr/bin/env python3

"""Setup script"""

import os
from setuptools import setup, find_packages

setup(
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: "
        "GNU General Public License v2 or later (GPLv2+)",
        "Programming Language :: Python :: 3",
        "Topic :: Security",
        "Topic :: System :: Systems Administration :: Authentication/Directory",
    ],
    packages=find_packages(exclude=['test']),
    use_scm_version=True,
    setup_requires=[
        'setuptools_scm',
    ],
    install_requires=([
        'alembic',
        'pyasn1',
        'pyyaml',
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
)
