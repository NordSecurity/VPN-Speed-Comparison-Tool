#!/bin/bash

set -x

define RESOLVE_CONF <<'EOF'
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF

sudo su -c 'umount /etc/resolv.conf'
echo "${RESOLVE_CONF}" | sudo bash -c "tee  > /etc/resolv.conf"
sudo service purevpn start
/bin/bash