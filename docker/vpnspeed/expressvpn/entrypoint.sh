#!/bin/bash
set -x

read -r -d '' RESOLVE_CONF <<'EOF'
nameserver 8.8.8.8
nameserver 127.0.0.11
EOF

sudo umount /etc/resolv.conf
echo "${RESOLVE_CONF}" | sudo bash -c "tee  > /etc/resolv.conf"
sudo /usr/bin/express-restart.sh && /bin/bash