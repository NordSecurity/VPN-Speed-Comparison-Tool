#!/bin/bash

set -ue

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../" >/dev/null 2>&1 && pwd )"
DOCKERDIR="$BASEDIR/docker"
DRY_RUN="${1:-"none"}"

function prn() {
    echo ""
    echo -e "$1"
    echo ""
}

command_exists() {
	command -v "$@" >/dev/null 2>&1
}

#Minimal versions:
#debian:10, ubuntu:18.04
verify_debian() {
    if [[ -f /etc/os-release ]]; then
        rez=$(cat /etc/os-release | grep ID | grep debian )
        [[ ! -z "$rez" ]] && return 0
    fi
    return 1
}

verify_debian || {
    prn "Deploy script has to be run on Linux Debian based system!"
    exit -1
}

OS="$(cat /etc/os-release  | grep -oP "^ID=\K.*")"
OS_VERSION_CODENAME="$(cat /etc/os-release  | grep -oP "VERSION_CODENAME=\K.*" )"

command_exists git || {
    prn "git is not installed, installing..."
    apt update && apt install -y git
}

export COMPOSE_INTERACTIVE_NO_CLI=1

prn "SETUP HOST CLI"
apt update
apt install -y python3-dev python3-pip python3-yaml python3-setuptools python3-wheel jq
PIP3="pip3"

# Install python 3.8 for debian 10
export $(grep VERSION_ID /etc/os-release)
if [[ $VERSION_ID  == \"10\" ]] ; then
    prn "SETUP PYTHON..."
    apt install -y zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libsqlite3-dev libreadline-dev libffi-dev libbz2-dev curl
    cd /opt && curl -O https://www.python.org/ftp/python/3.8.2/Python-3.8.2.tar.xz && \
         tar -xf Python-3.8.2.tar.xz && \
        cd Python-3.8.2 && ./configure --enable-optimizations && make -j$(nproc) && make altinstall
    PIP3="pip3.8"
fi

#Update pip3 to latest
${PIP3} install --upgrade pip

${PIP3} install -U "$BASEDIR/src/cli"

prn "SETUP DOCKER..."

apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg
curl -fsSL https://download.docker.com/linux/$OS/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/${OS} ${OS_VERSION_CODENAME} stable edge test"
apt update
apt install -y docker-ce
systemctl start docker
systemctl enable docker
curl -L "https://github.com/docker/compose/releases/download/1.26.2/docker-compose-Linux-x86_64" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

prn "SETUP HOST WIREGUARD"

#Add backports to buster
[[ "${OS_VERSION_CODENAME}" == "buster" ]] && apt-add-repository "deb http://deb.debian.org/debian buster-backports main" && apt update


apt install -y wireguard

prn "CHECK ENV..."

which docker
which docker-compose
docker images
docker ps

prn "SETUP VPN SPEED TEST..."

cd $DOCKERDIR

prn "BUILD DOCKER IMAGES..."

docker-compose down --volumes --rmi local || true
./dockerBuild.sh rebuild vpnspeedimages
docker image prune -f
docker-compose up -d --build

prn "CHECK ACTIVE DOCKER CONTAINERS..."

docker-compose ps runner

prn "WAIT FOR DOCKER CONTAINER TO START..."

sleep 30

[[ "${DRY_RUN}" == "--dry-run" ]] && { echo "Dry run selected, installation completed!" ; exit 0 ; }

prn "START SPEED TESTING..."

cd "$BASEDIR"

if ! vpnspeed up; then
    prn "FAILED TO START THE TESTS. CHECK OUTPUT AND TRY AGAIN"
    exit -1
fi

prn "CHECK IF TESTING STARTED..."

if ! vpnspeed context state | grep -q run; then
    prn "THE TESTS ARE NOT RUNNING. CHECK OUTPUT AND TRY AGAIN"
    exit -1
fi

prn "VPN SPEED TEST SHOULD BE RUNNING NOW"
prn "WAIT SOME TIME FOR TEST DATA TO GROW..."
