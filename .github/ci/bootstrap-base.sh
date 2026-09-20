#!/bin/bash
# Fetch the official Debian amd64 rootfs without requiring Docker Hub access.
set -euo pipefail
image=betterlinuxcnc-base:trixie-20260918
if docker image inspect "$image" >/dev/null 2>&1; then exit 0; fi
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# Official docker-debian-artifacts OCI layer, pinned to an immutable commit.
# Its SHA256 is recorded in trixie/oci/index.json at the same revision.
revision=8f962b15d7884a90e17876a9303cbac909d119aa
curl --fail --location --retry 3 --connect-timeout 20 --max-time 300 \
  "https://raw.githubusercontent.com/debuerreotype/docker-debian-artifacts/$revision/trixie/oci/blobs/rootfs.tar.gz" \
  -o "$tmp/rootfs.tar.gz"
echo "6eefb2f5d3e91a6cfc577476bbec26bb63f0d0fc31f904493f400833783aa2c2  $tmp/rootfs.tar.gz" | sha256sum -c -
docker import --change 'CMD ["bash"]' "$tmp/rootfs.tar.gz" "$image"
