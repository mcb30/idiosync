#!/bin/sh

set -e
set -x

topdir=$(realpath $(dirname $0)/../..)
podman run -i -t --rm -h freeipa.example.org -v ${topdir}:/opt/idiosync \
       unipartdigital/freeipa-tester \
       "cd /opt/idiosync && \
        ./setup.py develop && \
	cd test/files && \
	./mkldif.sh example-org.yml"
