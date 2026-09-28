# 桌面与网页 CI

The only active workflow is **Desktop and Web CI** (`.github/workflows/ci.yml`).
It checks the Web UI, Python diagnostic service and Tauri desktop host. It
deploys only the static Web preview. Native AXIS artwork generation/Tk validation,
LinuxCNC Debian package builds and the full compatibility workflow have been removed
from the active pipeline. The native AXIS application itself has also been
removed. Source checks guard the removed build/install entries and exercise
the launcher's rejection of legacy AXIS configurations before controller startup.
LinuxCNC engine source and shared Python APIs remain; these lightweight checks
do not replace a Linux native build. See [removal boundaries](../../docs/native-axis-removal.md).

## Required checks and ownership

- **Workflow and deployment checks**: actionlint, ShellCheck, shell/Python syntax,
  diff checks, release-packaging tests and offline installer/rollback tests.
- **Web types, boundaries and build**: Node 24, `npm ci`, `npm run check`,
  `npm run build`, then the release-packaging CLI below.
- **Web browser tests**: downloads that exact build, verifies its checksums and
  commit, and exercises it with Playwright Chromium using Vite preview. It does
  not build again. The release metadata test must match the selected commit.
- **Python service**: Python 3.11 and 3.13, pinned build/lint tools, Ruff, wheel
  and source builds, then public CLI/socket tests against the installed wheel.
  Python 3.13 uploads `betterlinuxcnc-python` with the wheel and source archive.
- **Tauri desktop / Debian 13**: disposable Debian 13 container on an Ubuntu
  runner, with system dependencies, Node 24 and the project's pinned Rust
  toolchain restored from a BuildKit image-layer cache; formatting, Clippy, Rust-to-Python integration
  tests, then a locked release build. It checks the generated `.deb` metadata
  and contents and uploads `betterlinuxcnc-desktop-debian13`. This is the desktop
  host package, not the LinuxCNC engine or Python service. It does not install
  the Python wheel or start a service automatically.
- **CI Gate**: requires all five jobs to succeed. This exact name remains for
  existing branch protection. Failed/skipped dependencies fail the gate.

The first two jobs and gate retain the dedicated `betterlinuxcnc` self-hosted
runner (PVE CI VM 101). It needs Git, Python 3, GNU Make, ShellCheck, actionlint and access
to GitHub/npm; `actions/setup-node` supplies Node 24. Its runner version must
support Node 24 Actions (v2.327.1 or newer). The existing loopback proxy and npm
download cache may be reused. The Web build does not need Docker, ccache,
Tk, Xvfb, or a LinuxCNC installation.

Before source checks, `ensure-make.sh` installs the `make` package only if the
command is missing. This bootstrap requires root or passwordless sudo on the
Debian/Ubuntu runner; subsequent runs use the installed tool without invoking
apt. Make is needed for the AXIS-removal Makefile dry-run tests, even though
this job does not compile LinuxCNC. Desktop-container dependencies do not
provide tools to the separate source-checks runner.

Browser tests use a disposable Ubuntu 24.04 runner, where Playwright installs
its browser and OS dependencies. Deployment uses another disposable hosted
  runner with the staging environment secrets. Neither the self-hosted build
nor the browser tests receive deployment credentials. Fork PR code cannot run
on the persistent runner; same-repository collaborators remain trusted.

There are no path filters that could leave a required gate absent. Ordinary
superseded checks are cancelled. Existing branch policy remains: push to main
checks only; push/manual run on staging测试环境 deploys after checks; collaborators
may explicitly request deployment of another branch through workflow_dispatch.
One shared deployment lock prevents overlapping staging installations.

## Desktop environment cache

`.github/ci/desktop/Dockerfile` owns only the Debian 13 system dependencies and
build tools. Its build context contains no application source. The desktop job
reads the Rust version from `frontend/src-tauri/rust-toolchain.toml`, builds or
restores the image using BuildKit's GitHub Actions cache
(`desktop-debian13-amd64`), and loads it into the hosted runner's Docker engine.
No registry publication, new credentials, or persistent runner is required.
Provenance attestations are disabled for this local dependency image so build
timestamps cannot change its identity and invalidate the Cargo cache.

Ordinary source changes reuse the installed apt packages and Rust components.
The first build, an evicted/inaccessible cache, a changed Dockerfile or Rust
version, or an updated parent image can cause dependency installation again.
Parent image tags are checked on each build (`pull: true`). To deliberately
refresh apt packages without a parent-image change, increment `SYSTEM_DEPS_REV`
in the Dockerfile. Cache hits still incur image download/load time on a fresh
hosted runner; they remove repeated package installation, not all setup time.

Each run starts a new container with the current checkout mounted at
`/workspace` and executes `.github/ci/desktop-in-container.sh` as the runner's
UID/GID. The script preserves the formatting, lint, integration tests, Debian
package build and package inspection. Application code and `node_modules` are
not stored in the environment image; `npm ci` still installs the locked
dependencies. Separate caches retain npm downloads, Cargo downloads and Rust
compiler outputs. Cargo cache keys include the actual environment image ID,
lockfile and source commit, so a changed environment cannot restore compiler
outputs built against an older image. Old `.deb` bundles are removed before
packaging so a restored cache cannot supply the uploaded release.

For local Linux/amd64 reproduction (Docker is required):

```sh
rust_version=$(python3 -c 'import pathlib,tomllib; print(tomllib.loads(pathlib.Path("frontend/src-tauri/rust-toolchain.toml").read_text())["toolchain"]["channel"])')
docker build --platform linux/amd64 --provenance=false --build-arg "RUST_VERSION=$rust_version" \
  -t betterlinuxcnc-desktop-ci:current .github/ci/desktop
desktop_cache=$(mktemp -d)
mkdir -p "$desktop_cache/npm" "$desktop_cache/cargo"
docker run --rm --init --platform linux/amd64 --user "$(id -u):$(id -g)" \
  --env CI=true --env HOME=/tmp/desktop-home --env CARGO_HOME=/cache/cargo \
  --env CARGO_TERM_COLOR=always --env npm_config_cache=/cache/npm \
  --mount "type=bind,src=$PWD,dst=/workspace" \
  --mount "type=bind,src=$desktop_cache,dst=/cache" \
  betterlinuxcnc-desktop-ci:current bash .github/ci/desktop-in-container.sh
```

The GitHub cache service is used only in Actions; local Docker builds reuse
local layers. Testing the remote cache hit rate and measuring CI time saved
requires two successful workflow runs with access to the same cache scope.

## Static artifact contract

From the repository root:

```sh
npm --prefix frontend ci
npm --prefix frontend run check
npm --prefix frontend run build
python3 .github/ci/package-web.py --dist frontend/dist --output web-artifact --commit "$(git rev-parse HEAD)"
```

The output directory must not already exist. The artifact `betterlinuxcnc-web`
contains exactly `web.tar.gz`, `COMMIT`, and `SHA256SUMS`. The archive contains
only static build files plus `build-info.json` with the full commit and
`interface: web`; no Node runtime, LinuxCNC source, `.deb`, deploy script or
secret is included. Symbolic links, stale release metadata and invalid commit
identifiers are rejected. `package-web.py` owns this CLI; tests use its public
command rather than importing its implementation.

The browser job unpacks the downloaded archive into `frontend/dist`, sets
`PLAYWRIGHT_TEST_DIST=1` and `EXPECTED_COMMIT`, and runs `npm run test:e2e` against
port 4173. Ordinary local tests still use the development server on port 5173.
Screenshots and traces are uploaded if browser checks fail.

Deployment transport, checksum verification, atomic activation, HTTP health
checks and rollback belong to [`.github/staging`](../staging/README.md). Existing
VMs require its one-time Web installer/nginx migration before their first Web
release. A repository edit or successful local test does not migrate a server.

## Local verification

```sh
.github/ci/check-source.sh
python3 -m unittest discover -s .github/ci -p 'test_*.py'
python3 -m unittest discover -s .github/staging -p 'test_*.py'
```

The old `run.sh`, container packaging helpers and `.github/scripts/` remain
available as manual LinuxCNC source-build tools. No active workflow invokes
them; they do not publish the Web or reinstall AXIS on staging.

References: [setup-node](https://github.com/actions/setup-node) and
[Playwright CI](https://playwright.dev/docs/ci-intro). Browser tests on Ubuntu or
macOS, and headless Debian package builds, do not replace desktop acceptance
on the target Debian 13/Intel graphics machine. See the [desktop startup and
verification commands](../../frontend/README.md) and [Python service guide](../../backend/README.md).
