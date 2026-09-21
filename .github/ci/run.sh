#!/bin/bash
# Host entry point: reusable dependencies, clean build filesystem each run.
set -euo pipefail
[[ ${1:-build} == build ]]
root=$(git rev-parse --show-toplevel)
cd "$root"
.github/ci/prepare-image.sh
image=betterlinuxcnc-ci:trixie
mkdir -p artifacts
container="betterlinuxcnc-build-$$"
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
docker run --rm --init --name "$container" --cpus=4 --memory=6g --memory-swap=6g \
  --tmpfs /work:rw,exec,size=3g --workdir /work \
  --mount "type=bind,src=$root,dst=/source,readonly" \
  --mount "type=bind,src=$root/artifacts,dst=/output" \
  --mount type=volume,src=betterlinuxcnc-ccache,dst=/ccache \
  -e "OUTPUT_UID=$(id -u)" -e "OUTPUT_GID=$(id -g)" \
  "$image" bash /source/.github/ci/build-in-container.sh
