#!/bin/bash

set -ex

SCRIPT_DIR="${SCRIPT_DIR:-$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )}"
TEMP_DIR="$(mktemp -d)"

cd $TEMP_DIR

curl -s https://my.surfshark.com/vpn/api/v1/server/configurations -o configurations.zip 
unzip -qq configurations.zip -d tmpConfiguration 
cat "tmpConfiguration/$(ls -1 tmpConfiguration | head -n 1)" | tr "\n" "|" | grep -o '<ca>.*</ca>' | sed 's/\(<ca>\|<\/ca>\)//g;s/|/\n/g' | sed '1,1d' | sed '$d' > ${SCRIPT_DIR}/SurfShark.pem

rm -rf ${TEMP_DIR}