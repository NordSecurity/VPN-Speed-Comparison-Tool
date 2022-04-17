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
#Update pip3 to latest
pip3 install --upgrade pip

pip3 install -U "$BASEDIR/src/cli"

prn "SETUP DOCKER..."

apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg
curl -fsSL https://download.docker.com/linux/$OS/gpg | apt-key add -
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce
systemctl start docker
systemctl enable docker
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

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
