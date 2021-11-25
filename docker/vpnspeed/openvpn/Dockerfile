FROM vpnspeed
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install openvpn && \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y autoremove --purge && \
    apt-get clean

ADD resource/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh