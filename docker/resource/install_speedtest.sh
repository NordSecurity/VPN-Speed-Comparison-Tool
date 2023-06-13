#/bin/bash
### Removing existing installation
rm /etc/apt/sources.list.d/speedtest.list || echo "[INFO] speedtest.list not found!"
apt-get update && apt-get remove -y speedtest || echo "[INFO] speedtest not found!"
### If Other non-official binaries is installed
apt-get remove -y speedtest-cli || echo "[INFO] speedtest-cli not found"

### Installing speed test
echo "[INFO] Instaling speedtest"
curl -s https://install.speedtest.net/app/cli/install.deb.sh | bash

#Fix signed issue
sed -i 's/\[.*\]/\[trusted=yes\]/g' /etc/apt/sources.list.d/ookla_speedtest-cli.list && apt-get update

apt-get install -y speedtest