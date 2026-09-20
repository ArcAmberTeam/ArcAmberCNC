#!/bin/bash
# Host entry point: reusable dependencies, clean build filesystem each run.
set -euo pipefail
mode=${1:-build}
[[ $mode == build || $mode == test ]]
root=$(git rev-parse --show-toplevel)
cd "$root"
.github/ci/bootstrap-base.sh
image=betterlinuxcnc-ci:trixie
# Only packaging inputs enter the image; application sources are never cached
# in a layer. Docker invalidates dependencies when these inputs change.
tar -cf - .github/ci/Dockerfile debian |
  docker build -f .github/ci/Dockerfile -t "$image" -
mkdir -p artifacts
container="betterlinuxcnc-build-$$"
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
capabilities=()
if [[ $mode == test ]]; then capabilities=(--cap-add=IPC_OWNER --cap-add=SYS_ADMIN); fi
docker run --rm --init --name "$container" --cpus=4 --memory=6g --memory-swap=6g \
  "${capabilities[@]}" \
  --tmpfs /work:rw,size=3g --workdir /work \
  --mount "type=bind,src=$root,dst=/source,readonly" \
  --mount "type=bind,src=$root/artifacts,dst=/output" \
  --mount type=volume,src=betterlinuxcnc-ccache,dst=/ccache \
  -e "OUTPUT_UID=$(id -u)" -e "OUTPUT_GID=$(id -g)" \
  "$image" bash /source/.github/ci/build-in-container.sh "$mode"
