FROM vpnspeed

RUN echo "deb http://deb.debian.org/debian/ buster-backports main contrib non-free" > /etc/apt/sources.list.d/unstable.list && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install openvpn wireguard
RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y autoremove --purge && \
    apt-get clean
RUN echo '#!/bin/bash' > /usr/bin/gen_wg_pub_key && echo 'echo $(echo "$1" | wg pubkey)' >> /usr/bin/gen_wg_pub_key
RUN chmod +x /usr/bin/gen_wg_pub_key
ADD resource/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
