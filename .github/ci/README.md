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
the packages and runs the upstream runtime suite, and is selected after
a push or manual run on `staging测试环境`, or when a collaborator selects their
own branch in **Run workflow** and enables `deploy_staging`. PRs do not install packages or run
the full runtime suite.

## Required checks

All four checks and their final `CI Gate` run on the self-hosted runner:

- **Debian 13 x86 build**: compile and package, using dependency and compiler caches.
- **Workflow and source checks**: actionlint, ShellCheck and shell syntax for
  maintained CI/deployment scripts, renderer syntax, changed Python syntax,
  diff whitespace/conflict markers, and four package-version regressions.
- **AXIS GIF and Tk checks**: validate all 21 manifest entries, SVG sources,
  dimensions, transparency and static frames; load each GIF with actual Tk
  under Xvfb and reject PNG files that would shadow the GIF.
- **G-code interpreter regressions**: download and checksum the same-run
  artifact, extract it without installing packages, and run eight upstream
  interpreter fixtures with exact expected-output comparisons and timeouts.
  This container has no network and does not start realtime motion.

Host tools are provisioned once: `shellcheck`, `python3-pil`, `python3-tk`,
`xvfb`, `xauth`, `nodejs`, and checksum-verified actionlint 1.7.7.
LinuxCNC and its package dependencies remain inside build/test containers.

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

Only the deployment job stays on a short-lived GitHub-hosted runner.
Deployment environment credentials are not passed to the persistent CI
runner. The manual `Full compatibility CI` matrix also uses the self-hosted
runner, with one disposable container per GCC/Clang/RTAI/HTML or Debian package
combination. `compatibility.sh` owns this host interface and delegates to
`compatibility-in-container.sh`; package installation never modifies the host.
The Docker daemon uses the loopback proxy to pull official Debian images.
Manual containers use host networking to reach that proxy, with CPU/RAM limits.
The runner executes one job at a time; additional parallel jobs need another
runner instance and sufficient CPU/RAM. The manual matrix is serialized and
can occupy this runner for a long time; run it outside active PR iteration.

This runner uses a loopback Mihomo HTTP proxy at `127.0.0.1:7897` through its
systemd service environment to reach GitHub reliably. The subscription is
stored privately on the CI VM, outside the repository. The proxy starts on
boot and exposes no LAN or public listener. It currently uses the imported
node snapshot; automatic subscription refresh is deferred until a working
replacement subscription URL is supplied.
