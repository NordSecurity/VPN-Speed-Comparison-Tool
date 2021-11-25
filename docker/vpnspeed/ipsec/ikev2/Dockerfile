FROM vpnspeed
RUN echo "deb http://deb.debian.org/debian/ buster-backports main contrib non-free" > /etc/apt/sources.list.d/unstable.list && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install \
               libssl-dev unzip strongswan libstrongswan-standard-plugins libcharon-extra-plugins libstrongswan-extra-plugins &&\
    DEBIAN_FRONTEND=noninteractive apt-get -q -y autoremove --purge && \
    apt-get clean

RUN wget https://downloads.nordvpn.com/certificates/root.der -O /etc/ipsec.d/cacerts/NordVPN.der && \
    openssl x509 -inform der -in /etc/ipsec.d/cacerts/NordVPN.der -out /etc/ipsec.d/cacerts/NordVPN.pem

ADD resource/cacerts/* /etc/ipsec.d/cacerts/
RUN chmod a+x /etc/ipsec.d/cacerts/get_usertrust_cert.sh
RUN chmod a+x /etc/ipsec.d/cacerts/get_SurfShark_cert.sh
RUN /etc/ipsec.d/cacerts/get_usertrust_cert.sh
RUN /etc/ipsec.d/cacerts/get_SurfShark_cert.sh
ADD resource/ipsec.conf /etc/ipsec.conf
ADD resource/constraints.conf /etc/strongswan.d/charon/constraints.conf
ADD resource/kernel-netlink.conf /etc/strongswan.d/charon/kernel-netlink.conf

ADD resource/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh