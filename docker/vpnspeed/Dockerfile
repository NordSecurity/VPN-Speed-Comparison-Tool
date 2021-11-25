FROM debian:10

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install \
                procps kmod curl wget procps expect ca-certificates acl \
                iptables iputils-ping iproute2 iputils-ping cron \
                python3-dev python3-pip python3-yaml python3-setuptools python3-wheel && \
    apt-get install -y debconf-utils && echo resolvconf resolvconf/linkify-resolvconf boolean false | debconf-set-selections && apt-get -y install resolvconf && \
    apt-get -o Dpkg::Options::="--force-confmiss" install --reinstall netbase && \ 
    DEBIAN_FRONTEND=noninteractive apt-get -q -y autoremove --purge && \
    apt-get clean

RUN pip3 install --upgrade pip
RUN echo '#!/bin/bash' > /usr/bin/write_to_file && echo 'echo -e "$1" > "$2"' >> /usr/bin/write_to_file
RUN chmod +x /usr/bin/write_to_file
RUN echo '#!/bin/bash' > /usr/bin/run_sub_proc && echo 'nohup $@ &>/var/log/nohup.out &' >> /usr/bin/run_sub_proc && \
    echo 'echo $!' >> /usr/bin/run_sub_proc
RUN chmod +x /usr/bin/run_sub_proc

ADD resource/install_speedtest.sh /tmp/install_speedtest.sh
RUN chmod +x /tmp/install_speedtest.sh
RUN /tmp/install_speedtest.sh
RUN speedtest --accept-license --accept-gdpr