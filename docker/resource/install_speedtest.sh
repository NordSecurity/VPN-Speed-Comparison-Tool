#/bin/bash
curl -s https://install.speedtest.net/app/cli/install.deb.sh | bash

#Fix signed issue
sed -i 's/\[.*\]/\[trusted=yes\]/g' /etc/apt/sources.list.d/ookla_speedtest-cli.list && apt-get update

apt-get install -y speedtest