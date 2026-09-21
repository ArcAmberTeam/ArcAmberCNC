# BetterLinuxCNC Web staging

The staging pipeline publishes the browser application built from `frontend/`.
Its artifact is `betterlinuxcnc-web`; CI/CD no longer builds or installs an AXIS
Debian package, starts LinuxCNC, requires an RT kernel, or executes motion tests.
The deployed application is a static Web interface with no machine connection.

## Deploy a repository branch

1. Push the branch with the current `.github/workflows/ci.yml`.
2. Open **Actions → Web CI → Run workflow** and select the branch.
3. Enable deployment to the shared test VM and run the workflow.
4. Wait for **CI Gate** and **Deploy Web to test machine**. Open the existing noVNC
   desktop and launch **BetterLinuxCNC Web**, or refresh its Chromium window.

The artifact is built from the immutable commit selected by that workflow run.
`staging测试环境` keeps automatic deployment after its checks pass; explicitly
requested branch deployments use the same gate. Pull requests and releases do
not deploy. Repository collaborators need permission to run Actions. The
existing GitHub `staging` environment, pinned SSH credentials, and concurrency
policy remain in use; the last successful deployment becomes the shared VM's
active Web version. The pipeline does not merge branches or deploy production.
See [CI operations](../ci/README.md) for the build runner and checks.

## Artifact contract

The downloaded artifact directory contains exactly:

```text
web.tar.gz
COMMIT
SHA256SUMS
```

- `COMMIT` is the selected 40-character lowercase commit SHA followed by one
  newline. The CI-side transport requires it to equal `GITHUB_SHA`.
- `SHA256SUMS` contains exactly the SHA-256 entries for `web.tar.gz` and `COMMIT`
  in standard `sha256sum` format. Either entry order is accepted.
- `web.tar.gz` has the Web build at its root: nonempty `index.html`, `assets/`,
  and `build-info.json` containing `{"commit":"<same SHA>","interface":"web"}`.
  There is no enclosing `dist/` directory, installer, or executable server.

The archive is bounded to 64 MiB compressed and 256 MiB expanded, with at most
10,000 entries and 64 MiB per file. Only directories and regular files are
accepted. Absolute paths, parent traversal, backslash paths, duplicate paths,
symlinks, hard links, devices, FIFOs, and sparse entries are rejected. Ownership
and executable permission bits in the archive are ignored; published files are
0644 and directories 0755. Uploaded JavaScript is served as browser content;
no uploaded code is run by the privileged installer.

## Deployment boundary

`deploy.sh` runs on the GitHub runner. `web_release.py verify-bundle` checks the
artifact's exact file set, commit, and checksums before transport. Strict SSH
host-key verification uses the pinned environment secret. Directory creation
and upload each have three attempts bounded to 180 seconds plus a 10-second
termination grace period, with a five-second delay between attempts. Only
idempotent transport is retried; the privileged deployment call runs once.

The remote entry point is **`/usr/local/sbin/betterlinuxcnc-deploy-web`**. An old
VM with only `betterlinuxcnc-deploy` fails with an explicit provisioning-upgrade
message. The transport never falls back to that obsolete package installer.

`install.sh` is provisioned as this root-owned entry point and calls the
root-owned `/usr/local/lib/betterlinuxcnc/web_release.py` in Python isolated
mode. The `deploy` user may sudo only the new entry point, whose only accepted
argument is `<run-id>-<attempt>-<commit>`. Neither file comes from the artifact.

```text
/srv/betterlinuxcnc-web/
  incoming/<run-id>-<attempt>-<commit>/   # deploy-owned upload staging
  releases/<run-id>-<attempt>-<commit>/   # root-owned static document roots
  current -> releases/<accepted-release>
```

The helper locks deployments, snapshots uploaded files without following
symlinks, validates their checksums and archive contents, and extracts into a
private temporary directory. It then atomically switches `current` and fetches
`build-info.json` and `index.html` through local HTTP. Acceptance requires the
served commit to match the release and the served index bytes to match the
artifact. HTTP failures or stale content restore the previous pointer and
report deployment failure. A failed first deployment removes `current` again.
Accepted releases remain available for inspection; this does not change the
operating system, installed LinuxCNC package, or kernel. Disk retention can be
managed separately by an administrator; ordinary deployment deletes no older
accepted releases.

## VM environment and one-time migration

The dedicated VM retains its existing administration interfaces:

- PVE VM `100`, `linuxcnc-staging`, tag `xamber`.
- Debian 13 amd64; existing RT kernels may remain installed but are not required.
- FRP relay `45.192.97.209:39010`.
- SSH `deploy@45.192.97.209:39011`, dedicated key authentication.
- HTTPS noVNC `https://45.192.97.209:39012/vnc.html`, separate VNC password.
- Web server **`http://127.0.0.1:8080/`**, accessible inside the VM's Chromium.

**Existing machines need one administrator-run provisioning upgrade before
these workflow changes can deploy.** From a trusted, reviewed checkout of this
revision, copy the complete `.github/staging/` directory to the VM using the
existing authenticated administration connection. On the dedicated VM, run:

```sh
sudo bash /path/to/reviewed-checkout/.github/staging/provision-vm.sh
```

The script expects cloud-init users `deploy` and `linuxcnc`, the already pinned
`/etc/frp/frpc.toml` and `server.crt`, and a checksum-verified `frpc` binary.
It provisions both root-owned helper files, revokes the old package-helper
sudo rule, removes its obsolete helper and desktop shortcut, installs Chromium
and nginx, and adds the **BetterLinuxCNC Web** shortcut. It does not uninstall
existing LinuxCNC packages, terminate a machining process, or modify FRP ports.
The old `/srv/betterlinuxcnc/` package history is left in place and is no longer
used by this pipeline.

Provisioning manages the dedicated VM's nginx configuration. It stops and
runtime-masks nginx during package installation to prevent the distribution's
default configuration from briefly listening on public port 80, then installs a
configuration with only `127.0.0.1:8080` and starts the service. A provisioning
failure before configuration validation leaves nginx stopped/masked; fix that
failure and rerun provisioning. The first page appears after the first accepted
Web deployment. Refresh an existing browser tab after a successful deployment.

TigerVNC still binds `127.0.0.1:5901`; HTTPS noVNC binds `127.0.0.1:6080`. Only
the existing noVNC HTTPS tunnel is publicly forwarded. No Web listener or new
FRP port is exposed. The self-signed noVNC certificate fingerprint should be
verified against provisioning records before trusting it. Its password remains
in `/root/staging-credentials/novnc-password`, and its certificate is
`/etc/novnc/server.crt`. The desktop user/service names retain `linuxcnc` for
compatibility with the existing VM account, not to launch the native UI.

## GitHub environment

Keep the environment named `staging` and its existing deployment history. To
permit explicitly requested repository branch deployments, configure its branch
policy accordingly; the workflow still enforces a branch ref and CI Gate.

Required environment secrets:

- `STAGING_SSH_KEY`: dedicated deployment private key.
- `STAGING_KNOWN_HOSTS`: pinned VM SSH public host key, recorded as
  `[45.192.97.209]:39011 ssh-ed25519 ...`. Obtain it through authenticated VM
  administration, not an unverified runtime key scan.

Optional environment variables `STAGING_HOST` and `STAGING_PORT` override the
relay destination; changing it also requires the corresponding pinned host key.
The workflow's deployment user remains `deploy`. No FRP token or relay root
credential is required by CI.

## Local verification

Only offline code validation was performed for this migration; editing these
files does not upgrade the VM or publish an artifact. The release tests run the
public Python CLI in temporary directories against a loopback HTTP server and
cover accepted releases, checksums/commit mismatches, unsafe archives, stale
HTTP content, and rollback. They never invoke SSH, apt, or LinuxCNC.

```sh
bash -n .github/staging/deploy.sh .github/staging/install.sh .github/staging/provision-vm.sh
shellcheck .github/staging/deploy.sh .github/staging/install.sh .github/staging/provision-vm.sh
python3 -m unittest discover -s .github/staging -p 'test_*.py'
```

The nginx/systemd provisioning must still be exercised by the administrator on
the dedicated Debian VM during the one-time upgrade. This local macOS checkout
cannot substantiate that the VM was upgraded or that a remote deployment passed.
