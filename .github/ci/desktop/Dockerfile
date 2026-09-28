# Only tools and system dependencies belong in this image; never COPY project code.
ARG RUST_VERSION=1.97.1
FROM node:24-bookworm-slim AS node
FROM rust:${RUST_VERSION}-slim-trixie

# Increment to refresh apt packages even when the parent image has not changed.
ARG SYSTEM_DEPS_REV=1
RUN echo "System dependency revision: ${SYSTEM_DEPS_REV}" \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl git build-essential pkg-config libssl-dev \
       libwebkit2gtk-4.1-dev libxdo-dev libayatana-appindicator3-dev \
       librsvg2-dev patchelf file python3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && rustup component add rustfmt clippy \
    && node --version && npm --version && rustc --version \
    && pkg-config --modversion webkit2gtk-4.1

WORKDIR /workspace
