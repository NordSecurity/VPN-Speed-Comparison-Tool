FROM vpnspeed
RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install \
                systemd sudo libglib2.0-0 iptables vim curl git

RUN echo "deb http://deb.debian.org/debian/ buster-backports main contrib non-free" > /etc/apt/sources.list.d/unstable.list && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install openvpn wireguard build-essential
RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y autoremove --purge && \
    apt-get clean
RUN mkdir /opt/wg && cd /opt/wg && git clone https://git.zx2c4.com/wireguard-tools && \
    make -C wireguard-tools/src -j$(nproc) && make -C wireguard-tools/src install && cd -

RUN curl -sSf https://downloads.nordcdn.com/apps/linux/install.sh -o /tmp/nordvpn_install.sh && chmod +x /tmp/nordvpn_install.sh
RUN yes | /tmp/nordvpn_install.sh

ENV TZ=Europe/Amsterdam
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y nordvpn

ADD /resource/nordvpn-restart.sh /usr/bin/nordvpn-restart.sh
RUN chmod a+x /usr/bin/nordvpn-restart.sh

ADD /resource/nordvpn-connect /usr/bin/nordvpn-connect
RUN chmod a+x /usr/bin/nordvpn-connect

ADD /resource/nordvpn-login /usr/bin/nordvpn-login
RUN chmod a+x /usr/bin/nordvpn-login

ADD /vpnspeed/nordvpn/entrypoint.sh /entrypoint.sh 
RUN chmod a+x /entrypoint.sh
