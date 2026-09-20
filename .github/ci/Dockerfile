FROM betterlinuxcnc-base:trixie-20260918
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -q -o Acquire::Retries=3 -o APT::Update::Error-Mode=any update \
    && apt-get --yes --no-install-recommends install \
       ca-certificates curl git lsb-release python3 devscripts sudo adduser xauth ccache
COPY debian /tmp/linuxcnc/debian
WORKDIR /tmp/linuxcnc
RUN debian/configure \
    && apt-get -q -o Acquire::Retries=3 -o APT::Update::Error-Mode=any update \
    && apt-get --yes build-dep --arch-only . \
    && rm -rf /tmp/linuxcnc
# debuild sanitizes PATH; configure its supported ccache entry point.
RUN printf '\nDEBUILD_PREPEND_PATH=/usr/lib/ccache\n' >> /etc/devscripts.conf \
    && printf 'cache_dir = /ccache\nmax_size = 5G\ncompiler_check = content\n' > /etc/ccache.conf
WORKDIR /work/linuxcnc
