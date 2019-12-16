#!/bin/sh

set -e
set -x

# Run test suite with coverage checks
#
python3 -m coverage erase
python3 -m coverage run --branch --source idiosync setup.py test
python3 -m coverage report --show-missing

# Run pycodestyle
#
python3 -m pycodestyle idiosync test

# Run pylint
#
python3 -m pylint idiosync test
