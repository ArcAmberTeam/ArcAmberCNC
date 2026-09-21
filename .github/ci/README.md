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
  runner, Node 24 and Rust 1.97.1; formatting, Clippy, Rust-to-Python integration
  tests, then a locked release build. It checks the generated `.deb` metadata
  and contents and uploads `betterlinuxcnc-desktop-debian13`. This is the desktop
  host package, not the LinuxCNC engine or Python service. It does not install
  the Python wheel or start a service automatically.
- **CI Gate**: requires all five jobs to succeed. This exact name remains for
  existing branch protection. Failed/skipped dependencies fail the gate.

The first two jobs and gate retain the dedicated `betterlinuxcnc` self-hosted
runner (PVE CI VM 101). It needs Git, Python 3, ShellCheck, actionlint and access
to GitHub/npm; `actions/setup-node` supplies Node 24. Its runner version must
support Node 24 Actions (v2.327.1 or newer). The existing loopback proxy and npm
download cache may be reused. The Web build does not need Docker, ccache,
Tk, Xvfb, or a LinuxCNC installation.

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
