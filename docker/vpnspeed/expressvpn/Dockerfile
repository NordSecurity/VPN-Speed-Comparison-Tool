FROM vpnspeed
RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install sudo iptables vim curl
ARG EXPRESSVPN_APP=expressvpn_3.10.0.9-1_amd64.deb
RUN wget -q "https://www.expressvpn.works/clients/linux/${EXPRESSVPN_APP}" -O /tmp/${EXPRESSVPN_APP} && \
    dpkg -i /tmp/${EXPRESSVPN_APP} && \
    rm -rf /tmp/*.deb 
ADD /resource/express-activate /usr/bin/express-activate
RUN chmod a+x /usr/bin/express-activate

ADD /resource/express-restart.sh /usr/bin/express-restart.sh
RUN chmod a+x /usr/bin/express-restart.sh

RUN echo "standard ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
RUN chmod a+x /tmp/${PIA_APP}
RUN useradd -ms /bin/bash standard
ADD /vpnspeed/expressvpn/entrypoint.sh /entrypoint.sh
RUN chmod a+x /entrypoint.sh
RUN chown standard /entrypoint.sh
USER standard
ENTRYPOINT [ "/entrypoint.sh" ]