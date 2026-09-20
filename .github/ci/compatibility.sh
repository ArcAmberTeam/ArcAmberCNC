#!/bin/bash
# Manual compatibility matrix host entry point. Never installs host packages.
set -euo pipefail
suite=${1:?suite}
dist=${2:?Debian release}
[[ $suite =~ ^(gcc|clang|rtai|html|package-arch|package-indep)$ ]]
[[ $dist =~ ^(bullseye|bookworm|trixie|sid)$ ]]
cd "$(git rev-parse --show-toplevel)"
out="$PWD/compat-artifacts/$suite/$dist"
mkdir -p "$out"
docker pull "debian:$dist"
container="betterlinuxcnc-compat-$$"
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
# Host networking gives the disposable container access to the loopback proxy.
docker run --rm --init --name "$container" --network=host \
  --cpus=4 --memory=6g --memory-swap=6g \
  --cap-add=IPC_OWNER --cap-add=SYS_ADMIN \
  -e http_proxy -e https_proxy -e no_proxy -e DEBIAN_FRONTEND=noninteractive \
  -e "OUTPUT_UID=$(id -u)" -e "OUTPUT_GID=$(id -g)" \
  --mount "type=bind,src=$PWD,dst=/source,readonly" \
  --mount "type=bind,src=$out,dst=/output" \
  "debian:$dist" bash /source/.github/ci/compatibility-in-container.sh "$suite" "$dist"
