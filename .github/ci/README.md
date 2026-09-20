# Dedicated Debian 13 CI

The `package-arch` job runs on repository runner `linuxcnc-ci-101`, with labels
`self-hosted`, `Linux`, `X64`, `betterlinuxcnc`. PVE VM 101 has 4 vCPUs, 8 GiB RAM
and a 64 GiB disk on the 500 GB HDD storage `hdd500`. The runner service runs as
`runner`, belongs to the Docker group, and starts on boot. It needs outbound
HTTPS access to GitHub, Actions endpoints, and Debian mirrors; no inbound
public CI port is required.

## Interface and isolation

Run `.github/ci/run.sh build` from a checkout to compile and produce Debian
packages in `artifacts/`, with `SHA256SUMS.txt`. The `test` mode also installs
the packages and runs the upstream runtime suite, and is selected only after
a push or manual run on `staging测试环境`. PRs only build.

`run.sh` is the host entry point. `build-in-container.sh` is its private
container implementation and calls the existing `.github/scripts` packaging
and verification commands. Deployment remains owned by `.github/staging`.

Every build copies a read-only checkout into a fresh disposable container.
Build dependencies are cached as image layers; only ccache compiler results
persist in the `betterlinuxcnc-ccache` Docker volume (maximum 5 GiB, compiler
content checked). No previous build directory is reused. Containers are
limited to 4 CPUs and 6 GiB RAM. The disposable build directory uses a 3 GiB
tmpfs within that memory budget to avoid HDD small-file writes; the VM disk,
dependency images, compiler cache and exported packages remain on `hdd500`.
Cancellation removes the build container.
Checkout does not retain GitHub credentials. Only same-repository PRs are
eligible for this persistent runner; a fork PR fails the gate without running
its build here. Repository writers and Docker access are trusted with this VM.

`bootstrap-base.sh` imports the official Debian Docker amd64 rootfs from
`debuerreotype/docker-debian-artifacts`, pinned by commit and SHA256. This
avoids the runner network's unavailable Docker Hub registry. Provenance is
the `trixie/oci/index.json` manifest at the pinned revision; the base image is
stored locally as `betterlinuxcnc-base:trixie-20260918`. Update the revision,
checksum and dated image name together when refreshing the base.

The dependency image is rebuilt when the Dockerfile or Debian packaging
inputs change. Dependency installation uses `eatmydata` only inside the
disposable image build layer to reduce HDD flushes. A failed layer is discarded.
For an OS dependency refresh without a packaging change,
rebuild it with `--no-cache` during runner maintenance. Do not prune the
ccache volume unless intentionally discarding compiler cache.

`CI Gate` and the deployment job stay on short-lived GitHub-hosted runners.
Deployment environment credentials are not passed to the persistent build
runner. The manual `Full compatibility CI` matrix also remains GitHub-hosted.
The runner executes one job at a time; additional parallel jobs need another
runner instance and sufficient CPU/RAM.

This runner uses a loopback Mihomo HTTP proxy at `127.0.0.1:7897` through its
systemd service environment to reach GitHub reliably. The subscription is
stored privately on the CI VM, outside the repository. The proxy starts on
boot and exposes no LAN or public listener. It currently uses the imported
node snapshot; automatic subscription refresh is deferred until a working
replacement subscription URL is supplied.
