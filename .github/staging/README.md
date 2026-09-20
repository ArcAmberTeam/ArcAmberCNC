# BetterLinuxCNC staging

`kihon` is the development branch, `staging` is the acceptance branch, and
`main` is the stable branch. Pushes (including merged PRs) to `staging` run
the existing x86 CI. Only a successful `CI Gate` permits deployment. PRs,
other branches, and releases never trigger this deployment job. Manual
`Build CI` runs on `staging` also build, test, and deploy.

## Environment

- PVE VM: `100`, `linuxcnc-staging`, orange `xamber` tag.
- Debian 13 amd64, 1 vCPU, 4096 MiB RAM, 32 GiB disk, PREEMPT_RT kernel.
- FRP relay: `45.192.97.209:39010` (dedicated instance).
- SSH: `deploy@45.192.97.209`, port `39011`, key authentication only.
- noVNC: `https://45.192.97.209:39012/vnc.html`, separate VNC password.
  The HTTPS certificate is initially self-signed; verify its fingerprint
  using the provisioning records before trusting it.
- This VM is for simulation only. A VM test is not a hardware latency or
  machine safety acceptance test.

`provision-vm.sh` installs the RT kernel, a minimal XFCE/TigerVNC desktop,
HTTPS noVNC, and the FRP client service. It expects the cloud-init users
(`root`, `deploy`, `linuxcnc`), pinned FRP certificate/configuration, and a
checksum-verified `frpc` binary to already exist. Upload `install.sh` as
root-owned `/usr/local/sbin/betterlinuxcnc-deploy` with mode 0755 first.
The distribution's LinuxCNC package is installed as a bootstrap version;
it is replaced by the repository's package only after CI passes.

The generated VNC password is saved only in
`/root/staging-credentials/novnc-password` on the VM. The TLS certificate is
`/etc/novnc/server.crt`; its fingerprint can be checked with
`openssl x509 -in /etc/novnc/server.crt -noout -fingerprint -sha256`.
Both the VNC server (5901) and noVNC (6080) bind to loopback. Only the HTTPS
noVNC endpoint is forwarded publicly. FRP verifies the relay's pinned TLS
certificate, and the independent relay instance permits only 39011–39012.

## GitHub configuration

Create a GitHub Environment named `staging`, with a deployment branch policy
that permits only the `staging` branch. No reviewer is required. A private
organization repository needs GitHub Team (or higher) for this environment.

Set these **environment secrets**, never commit their values:

- `STAGING_SSH_KEY`: the dedicated deployment private key.
- `STAGING_KNOWN_HOSTS`: the VM's public SSH host key, recorded as
  `[45.192.97.209]:39011 ssh-ed25519 ...`. Obtain it through the authenticated
  PVE/VM administration connection; do not blindly trust a runtime key scan.

Optional environment variables: `STAGING_HOST` and `STAGING_PORT` override the
relay address and port above. Changing the destination also requires changing
the pinned host key. The relay's root credentials and FRP token are not needed
by GitHub Actions.

## Deployment boundaries

`deploy.sh` runs on the GitHub runner. It checks the same-run
`linuxcnc-trixie-amd64` artifact's checksums, selects exactly one amd64
`linuxcnc-uspace` package, and uploads it with a commit identifier and smoke
fixture. It uses strict SSH host-key verification.

`install.sh` is provisioned once as root-owned
`/usr/local/sbin/betterlinuxcnc-deploy`. The `deploy` account may sudo only this
helper. Installing a Debian package executes its maintainer scripts as root;
the deployment credential therefore grants control of this disposable VM.
Never reuse the account, key, or helper on production.

The helper serializes deployments, requires Debian 13 amd64 and an active
realtime kernel, checks the uploaded package, installs it, and runs `smoke.py`
as the unprivileged `linuxcnc` user against the upstream simulation INI. The
test must produce an explicit success marker after XYZ homing, MDI motion,
position verification, and return to origin. There are no attached devices.

Accepted packages and logs remain in `/srv/betterlinuxcnc/releases/`.
`/srv/betterlinuxcnc/current` changes only after successful acceptance. On
installation/test failure, the helper attempts to reinstall and test the
previous accepted LinuxCNC package and still reports the deployment as failed.
This rollback does not roll back OS dependencies or kernel updates. On the
first deployment there is no previous accepted package to restore.

Close interactive LinuxCNC sessions before deployment. The desktop itself can
stay open. A busy simulation causes deployment to fail without interrupting it.
Changes to the root-owned installer require reprovisioning that helper;
ordinary deployments do not replace it with an uploaded script.

The pipeline does not merge into `main`, change `main` protection, or deploy
production. Enable the existing required `CI Gate` rule after upgrading the
organization plan.
