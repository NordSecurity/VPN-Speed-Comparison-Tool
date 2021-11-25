#!/bin/bash

set -ue

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../" >/dev/null 2>&1 && pwd )"
DOCKERDIR="$BASEDIR/docker"
DRY_RUN="${2:-}"

function prn() {
    echo -e "${1:-}"
}

function prn_w() {
    prn
    prn "$1"
    prn
}

REMOTE=${1:-no}

if [[ "${REMOTE}" == "no" ]]; then
    prn "Provide deploy location"
    prn "Usage: install_to.sh <REMOTE>"
    prn "Egz:   isntall_to.sh root@myhost"
    exit 1
fi

REMOTE_PKG="$REMOTE:/opt/vpnspeed.tar.gz"
REMOTE_PKGDIR="$REMOTE:/opt"

TMPDIR=$(mktemp -d)
PKG="$TMPDIR/vpnspeed.tar.gz"
PKGDIR="$TMPDIR/vpnspeed"

cp -r "$BASEDIR" "$PKGDIR"
prn_w "Creating package $PKG from $BASEDIR"
cd "$TMPDIR" && tar czvf $PKG --exclude ".**" --exclude "*.egg-info" --exclude "test" "vpnspeed"

# prn_w "Sending to $REMOTE..." 
scp $PKG $REMOTE_PKG
rm -rf $TMPDIR

# prn_w "Setuping in..."
ssh $REMOTE "
    rm -rf /opt/vpnspeed ;
    tar xzf /opt/vpnspeed.tar.gz -C /opt &&
    rm /opt/vpnspeed.tar.gz && 
    /opt/vpnspeed/scripts/setup.sh ${DRY_RUN}
"

prn_w "Finished deploying vpnspeed."
