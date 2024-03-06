FROM debian:10
ENV DOCKER_CLI_DEB="containerd.io_1.2.6-3_amd64.deb"
ENV DOCKER_CE_CLI_DEB="docker-ce-cli_19.03.9~3-0~debian-buster_amd64.deb"
ENV DOCKER_CONTAINERD_DEB="docker-ce_19.03.9~3-0~debian-buster_amd64.deb"
ENV DOCKER_DIST_POOL="https://download.docker.com/linux/debian/dists/buster/pool/stable/amd64"

RUN  apt-get update && \ 
        DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install \
        procps vim curl build-essential expect ca-certificates python3-dev python3-pip python3-setuptools python3-wheel

RUN mkdir -p /tmp/docker/
RUN curl -so /tmp/docker/${DOCKER_CLI_DEB} ${DOCKER_DIST_POOL}/${DOCKER_CLI_DEB} && \
        DEBIAN_FRONTEND=noninteractive apt-get -q -y install /tmp/docker/${DOCKER_CLI_DEB}

RUN curl -so /tmp/docker/${DOCKER_CE_CLI_DEB} ${DOCKER_DIST_POOL}/${DOCKER_CE_CLI_DEB} && \
        DEBIAN_FRONTEND=noninteractive apt-get -q -y install /tmp/docker/${DOCKER_CE_CLI_DEB}

RUN curl -so /tmp/docker/${DOCKER_CONTAINERD_DEB} ${DOCKER_DIST_POOL}/${DOCKER_CONTAINERD_DEB} && \
        DEBIAN_FRONTEND=noninteractive apt-get -q -y install /tmp/docker/${DOCKER_CONTAINERD_DEB}

# Setup python3.8
RUN  apt-get update && \
        DEBIAN_FRONTEND=noninteractive apt-get -q -y --no-install-recommends install \
        zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libsqlite3-dev libreadline-dev libffi-dev libbz2-dev
RUN cd /opt && curl -O https://www.python.org/ftp/python/3.8.2/Python-3.8.2.tar.xz && tar -xf Python-3.8.2.tar.xz &&  \
        cd Python-3.8.2 && ./configure --enable-optimizations && make -j$(nproc) && make altinstall

RUN pip3.8 install --upgrade pip
ADD ./ /opt/vpnspeed
RUN chmod +x /opt/vpnspeed/docker/dockerBuild.sh
RUN mkdir -p /var/run/vpnspeed
RUN pip3.8 install /opt/vpnspeed
ADD docker/runner/entrypoint.sh /entrypoint.sh
RUN chmod +x entrypoint.sh
WORKDIR /opt/vpnspeed
ENTRYPOINT [ "/entrypoint.sh" ]