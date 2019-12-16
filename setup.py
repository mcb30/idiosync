#!/usr/bin/env python3

"""Setup script"""

from setuptools import setup, find_packages

setup(
    name="idiosync",
    description="Synchronize user databases",
    author="Michael Brown",
    author_email="mbrown@fensystems.co.uk",
    license="GPLv2+",
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
    install_requires=[
        'alembic',
        'pyasn1',
        'python-ldap',
        'pyyaml',
        'sqlalchemy',
    ],
    entry_points={
        'console_scripts': [
            'idiosync=idiosync.cli:SynchronizeCommand.main',
        ],
    },
)
