FROM vpnspeed
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install vim ca-certificates curl sudo iproute2 net-tools iputils-ping expect
ARG PUREVPN_APP=purevpn_1.2.5_amd64.deb
RUN curl https://d3uym7n1flvv1x.cloudfront.net/linux/app/${PUREVPN_APP} -o /tmp/${PUREVPN_APP}
RUN dpkg -i /tmp/${PUREVPN_APP}
RUN useradd -ms /bin/bash standard
RUN chown standard /usr/bin/purevpn
RUN echo "standard ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
ADD /vpnspeed/pure/purevpn-cli.sh /usr/bin/purevpn-cli
RUN chmod a+x /usr/bin/purevpn-cli
ADD /vpnspeed/pure/purevpn-login.sh /usr/bin/purevpn-login
RUN chmod a+x /usr/bin/purevpn-login
ADD /vpnspeed/pure/entrypoint.sh /entrypoint.sh 
RUN chmod a+x /entrypoint.sh
USER standard