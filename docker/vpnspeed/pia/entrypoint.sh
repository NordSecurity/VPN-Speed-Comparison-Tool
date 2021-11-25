#!/bin/bash
su -c 'umount /etc/resolv.conf'

cat > /etc/resolv.conf <<EOF
nameserver 8.8.8.8
nameserver 127.0.0.11
EOF
nohup /opt/piavpn/bin/pia-daemon &> /var/log/pia_daemon.out & 
piactl background enable
/bin/bash