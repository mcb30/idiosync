#!/bin/bash

set -e
set -x

cfgfile=$1

function trace_start {
    tracefile=$1
    idiotrace ${cfgfile} -c .cookie -o "$@" &
    tracepid=$!
}

function trace_stop {
    sleep 1
    kill ${tracepid}
    cat ${tracefile}
}

rm -f .cookie

trace_start create-users.ldif
ipa user-add alice --first=Alice --last=Archer
ipa user-add bob --first=Bob --last=Baker
trace_stop

trace_start modify-users.ldif
ipa user-mod bob --first=Bobby
trace_stop
