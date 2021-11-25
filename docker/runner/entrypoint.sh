#!/bin/bash
su -c 'umount /etc/resolv.conf'

cat > /etc/resolv.conf <<EOF
nameserver 8.8.8.8
nameserver 127.0.0.11
EOF
cd docker
./dockerBuild.sh build vpnspeedimages
cd -
vpnspeedd $@
