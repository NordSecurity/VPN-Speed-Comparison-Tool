#!/bin/bash

SCRIPT_DIR="${SCRIPT_DIR:-$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )}"
TEMP_DIR="$(mktemp -d)"

cd $TEMP_DIR

curl -sL http://www.tbs-x509.com/USERTrustRSACertificationAuthority.crt -o usertrust.crt
openssl x509 -in usertrust.crt -out ${SCRIPT_DIR}/usertrust.pem -outform PEM 

rm -rf ${TEMP_DIR}