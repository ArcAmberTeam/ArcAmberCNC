FROM debian:13-slim
ENV DEBIAN_FRONTEND=noninteractive
COPY packages.txt /tmp/native-packages.txt
RUN apt-get update \
    && xargs -r apt-get install -y --no-install-recommends < /tmp/native-packages.txt \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
