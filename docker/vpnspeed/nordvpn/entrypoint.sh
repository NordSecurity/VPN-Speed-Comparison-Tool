#!/bin/bash

# set -x 

su -c 'umount /etc/resolv.conf'

cat > /etc/resolv.conf <<EOF
nameserver 8.8.8.8
nameserver 1.1.1.1
EOF
rm -rf /run/nordvpn/nordvpnd.sock || echo "Socket does not exist!"
/usr/bin/nordvpn-restart.sh && /bin/bash
