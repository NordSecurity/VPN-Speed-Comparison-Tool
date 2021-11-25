FROM vpnspeed
RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install \
                systemd sudo libglib2.0-0 iptables vim curl
RUN echo "deb http://deb.debian.org/debian/ buster-backports main contrib non-free" > /etc/apt/sources.list.d/unstable.list && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install openvpn wireguard
RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y autoremove --purge && \
    apt-get clean
RUN echo "standard ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
ARG PIA_APP=pia-linux-3.0.1-06696.run
RUN curl https://installers.privateinternetaccess.com/download/${PIA_APP} --output /tmp/${PIA_APP}
RUN chmod a+x /tmp/${PIA_APP}
RUN useradd -ms /bin/bash standard
USER standard
#Hacky way to install pia app -> 'System has not been booted with systemd as init system (PID 1). Can't operate'.
RUN /tmp/${PIA_APP} || echo "Install done.." 
USER root
ADD /vpnspeed/pia/entrypoint.sh /entrypoint.sh 
RUN chmod a+x /entrypoint.sh