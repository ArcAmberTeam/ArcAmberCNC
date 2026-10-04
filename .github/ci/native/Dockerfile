FROM debian:13-slim
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       autoconf automake build-essential ca-certificates file gettext git intltool \
       pkg-config procps psmisc python3-dev python3-tk python3-yapps yapps2 \
       libboost-python-dev libedit-dev libepoxy-dev libglib2.0-dev \
       libglu1-mesa-dev libxinerama-dev libxmu-dev libgpiod-dev libmodbus-dev \
       libtirpc-dev libudev-dev libusb-1.0-0-dev tcl8.6-dev tk8.6-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
