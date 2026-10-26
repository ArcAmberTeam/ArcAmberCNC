# LinuxCNC dedicated-appliance installation and maintenance

The application control chain always runs on the same host under the same operating account: QML → DesktopBackend → Unix socket → Python controller service → LinuxCNC. SSH is for maintenance, not machine-command transport.

This document distinguishes historically verified environments from `26.10.26.1` deployment steps. Written steps do not mean they were executed on the target; record commits, versions, and results for actual releases, migrations, login policies, and window checks separately. Local/target builds and source tests, including local Docker, are currently forbidden. GitHub CI alone builds/releases complete DEBs; targets only download, install, and accept runtime behavior.

## Historically verified environment

On 2026-10-25, the user authorized deployment under the old account through `teto@192.168.109.67`:

- Repository `/home/teto/ArcAmberCNC`, Debian 13, real-time kernel, Python 3.13.5, PySide6 6.8.2.1.
- Original `configs/zhulong-v2/烛龙V2.ini` used `DISPLAY = betterlinuxcnc`; root `launcher.json` contained existing INI, CAM address, and inbox settings.
- X11 then used `DISPLAY=:0`, `XAUTHORITY=/home/teto/.Xauthority`, control endpoint `/run/user/1000/betterlinuxcnc/control.sock`, and a 1024×600 GUI.
- After installation from `origin/main` `6a190df`, entry-point/QML hashes matched, the user service reported ready, and the GUI read real LinuxCNC state; the user confirmed usability.
- Existing `launcher.json`, INI, VERSION/changelog edits, and untracked machine configuration were preserved. No home, jog, spindle, tool-change, or machining commands were sent. Historical enable/emergency-stop state does not represent current state or motion acceptance.

Do not reuse these historical UIDs, Xauthority, or paths for the new `linuxcnc` account.

## 26.10.26.1 system paths and accounts

| Path | Content and permissions |
| --- | --- |
| `/usr/bin/betterlinuxcnc*` | Package-managed, root-owned application CLIs |
| `/usr/sbin/betterlinuxcnc-appliance` | Explicit host configuration; administrative operations require root |
| `/usr/lib/betterlinuxcnc`, `/usr/share/betterlinuxcnc` | Application modules, maintenance tools, QML; not user-writable |
| `/usr/lib/linuxcnc/modules/zhulong_homing.so` | Fixed HOMEMOD; explicitly enabled only after matching 2.9.10 core/header verification |
| `/usr/share/betterlinuxcnc/homing/provenance.json` | HOMEMOD/header hashes, source commit, software verification |
| `/etc/betterlinuxcnc/launcher.json`, `machine/` | Migrated startup/INI/HAL/configuration copies, root-owned |
| `/etc/betterlinuxcnc/updater.json` | Fixed root updater configuration, Debian conffile |
| `/usr/share/doc/betterlinuxcnc-qt/examples/launcher.example.json` | Example only; does not replace onsite configuration |
| `/var/lib/betterlinuxcnc/home` | `linuxcnc` HOME, 0700 |
| `/var/lib/betterlinuxcnc/{programs,inbox,machine}` | Programs, CAM inbox, mutable tool tables/parameters/positions, writable by `linuxcnc` |
| `/var/cache/betterlinuxcnc/user` | Private `linuxcnc` XDG cache |
| `/var/cache/betterlinuxcnc/update` | Root-private update cache/install logs |
| `/var/lib/betterlinuxcnc/recovery/snapshots` | Root-private configuration/machine snapshots, latest three |
| `/var/log/betterlinuxcnc/launcher` | `linuxcnc:cnc-logs`, directories 2750, process logs 0640 |
| `/run/user/<linuxcnc UID>/betterlinuxcnc/control.sock` | Private endpoint for this login; UID is not fixed |

Top-level `/var/lib/betterlinuxcnc`, `/var/cache/betterlinuxcnc`, and system configuration remain root-owned and unwritable by ordinary users. Do not recursively assign these roots to `linuxcnc`. Launcher `state.json`, socket, and locks remain private, not shared with the log group.

`linuxcnc` runs only the dedicated fullscreen X11 session/application without general sudo or SSH login. `cnc-maint` reads diagnostics through fixed SSH commands, without desktop login, shell, uploads, or elevation. System root remains for explicit host configuration/restricted updating, not routine root SSH login.

## Release package and installation preparation

Product version is `26.10.26.1`, Release name `demo v26.10.26.1`, tag `v26.10.26.1`. Official amd64 package is `betterlinuxcnc-qt_26.10.26.1_amd64.deb` with `SHA256SUMS`, published as non-prerelease latest. After PR merge into main with `build-release`, GitHub verifies same-commit CI/package and publishes automatically. See [application updates](firmware-updates.md).

Targets download completed Release DEBs/checksums and install through apt/dpkg. Do not fetch/build source or install Rust/CMake build tools. Preserve old repository `launcher.json`, machine directories, and VERSION/changelog edits for initial explicit migration review; never overwrite onsite files with reset/clean. GitHub source zip/tar is not a deployment package.

Before installing/switching sessions, reread machine state and have the operator perform normal shutdown. Confirm old launcher, LinuxCNC, and controller exited; never force-kill the core or interpret service active as machine idle. Preserve CAM `auto_run`; connection checks must not casually upload test programs.

The following runs only in the authorized target administrator environment. Fixed postinst automatically provisions accounts/directories, without prepare/activate, machine copies, login policy, or password creation/reset. LightDM, Xorg, and SSH install as runtime dependencies; activating dedicated policy remains explicit.

```sh
cd /var/tmp/betterlinuxcnc-release-v26.10.26.1
sha256sum --check SHA256SUMS
dpkg-deb --field betterlinuxcnc-qt_26.10.26.1_amd64.deb Package Version Architecture
sudo apt-get install ./betterlinuxcnc-qt_26.10.26.1_amd64.deb
```

## Explicit staging, preparation, and activation

Open and retain a trusted root maintenance session before migration. Activation restricts old `teto` SSH/sudo; an ordinary administrator shell is not an already-acquired root session. Supply maintenance passwords only through non-echoed stdin, never source, environment variables, arguments, packages, scripts, logs, or this document.

In the retained root session:

```sh
betterlinuxcnc-appliance plan
betterlinuxcnc-appliance stage \
  --source-config /home/teto/ArcAmberCNC/launcher.json \
  --destination /var/tmp/betterlinuxcnc-import-v26.10.26.1 \
  --zhulong-homing-travel-mm 420 275 90 --zhulong-xyz-only
```

The stage destination must not exist. It creates only a reviewable copy, without account/login-policy changes. Check migrated INI, HAL references, program directories, tool table, parameters, position files, and CAM inbox. Only G-code extensions enter the program library. Review symlinks, special files, INI includes, and CAM private-key/token paths separately first. Copies disable external editors/filters; originals stay unchanged.

`420 275 90` is the user's measured X/Y/Z total travel in mm supplied on 2026-10-26, not valid for other machines. This merges reviewed switches/homing into the existing copy, not a wholesale reference-INI replacement. stage marks installation verification pending. prepare must verify `linuxcnc-uspace` and `linuxcnc-uspace-dev` are both upstream 2.9.10, installed header hashes, HOMEMOD provenance, and binary hash. Stop if matching prebuilt development packages are missing; do not bypass with Debian 2.9.4 headers or target builds.

For switch-only integration, use mutually exclusive `--zhulong-inputs-only` in both commands and retain `motion.homing-inhibit=true`. Without either option, preserve original migration behavior. The user confirmed XYZ-only hardware, so the commands include `--zhulong-xyz-only`, strictly removing reviewed reserved ABC configuration/HAL wiring and setting actual joints to three while retaining spindle, other I/O, and six-stepgen board capacity. Without this option, retain real ABC homing interlocks; never fabricate homed state. The tool triggers no HOME or other motion.

Post-homing soft limits for this migration are X 0–410, Y −265–0, Z 0–80 mm, leaving 5 mm at each end. Preserve parameters/tool tables; after first actual homing, verify work coordinates such as G54 and tool length onsite. Old coordinates are not automatically validated for machining.

After review, prepare for the first time:

```sh
betterlinuxcnc-appliance prepare   --source-config /home/teto/ArcAmberCNC/launcher.json   --zhulong-homing-travel-mm 420 275 90 --zhulong-xyz-only
systemd-ask-password 'Set the dedicated maintenance account password' | betterlinuxcnc-appliance set-maintenance-password
runuser -u linuxcnc -- env HOME=/var/lib/betterlinuxcnc/home   XDG_CACHE_HOME=/var/cache/betterlinuxcnc/user   /usr/bin/betterlinuxcnc-launch --config /etc/betterlinuxcnc/launcher.json --check
```

The package already provisions accounts/directories idempotently. prepare explicitly copies configuration/runtime data without overwriting existing appliance configuration or starting LinuxCNC. Do not repeat on migrated machines during ordinary updates; reinstall/update does not reset maintenance passwords. `--check` validates configuration, dependencies, and startup plan, not hardware/connectivity.

After confirming preparation, activate explicitly:

```sh
betterlinuxcnc-appliance activate
/usr/sbin/sshd -t
/usr/sbin/sshd -T
/usr/sbin/visudo -c
```

Activation writes fixed LightDM/X11/logind, SSH, sudo, Polkit, and SysRq policy. The tool manages complete `/etc/ssh/sshd_config`, not drop-ins vulnerable to other Include/Match overrides. Main sudo configuration retains root rules only, removing old ordinary-account grants. Original policy contents, permissions, and recovery records are saved in root-private `/var/lib/betterlinuxcnc/recovery/<timestamp>/policies.json`.

activate enables only the Mesa check timer without card-write privileges; it does not reload SSH, restart graphics, or reboot. First verify effective `sshd -T` and visudo results, then reload SSH from the retained root session during the deployment window and verify new `cnc-maint` access. Accept LightDM/X11/logind/kernel policy after a controlled reboot, with the machine stopped and onsite recovery available. Keep the old root session until all checks pass. Without a generic SSH admin shell, controlled local administrators recover policy; maintenance commands must not bypass restrictions.

## Dedicated session and read-only connection acceptance

LightDM autologins `linuxcnc` into `betterlinuxcnc-kiosk` X11. The session runs `betterlinuxcnc-launch --kiosk-session`, imports actual DISPLAY/Xauthority, starts user `betterlinuxcnc-launcher.service`, and remains alive. Waiting/startup failure displays an independent status page without machine connection, not ordinary desktop/login selection. Do not start another launcher manually.

In the existing target root maintenance session, use the actual UID for read-only checks:

```sh
operator_uid=$(id -u linuxcnc)
runuser -u linuxcnc -- env XDG_RUNTIME_DIR="/run/user/$operator_uid" \
  DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$operator_uid/bus" \
  /usr/bin/systemctl --user status betterlinuxcnc-launcher.service --no-pager -l
runuser -u linuxcnc -- env XDG_RUNTIME_DIR="/run/user/$operator_uid" \
  /usr/bin/betterlinuxcnc --check-connection \
  --socket "/run/user/$operator_uid/betterlinuxcnc/control.sock"
dpkg-query -W -f='${Package} ${Version}\n' betterlinuxcnc-qt
```

`--check-connection` sends only `machine.status`, without session attachment/jog renewal; do not combine with `--ini`/`--program`. Exit 0 means machine connected, 2 service reachable/core disconnected, 1 endpoint/permission/protocol error. Use the user bus only after a real graphical login; do not substitute a temporary bus.

Check together: actual fullscreen/touch UI, current account, absence of ordinary desktop/terminal access, private current-run `state.json` ready, real status, and installed QML/Python versions. Process logs live in `/var/log/betterlinuxcnc/launcher/<current-start-directory>/`; do not reuse old PIDs/screenshots/`~/.local/state`. UI file selection is confined to programs/inbox, not general host browsing.

## Fixed SSH maintenance interface

After dedicated policy activation, only `cnc-maint@192.168.109.67` is allowed, with exactly one argument-free command:

```sh
ssh cnc-maint@192.168.109.67 help
ssh cnc-maint@192.168.109.67 version
ssh cnc-maint@192.168.109.67 status
ssh cnc-maint@192.168.109.67 logs
ssh cnc-maint@192.168.109.67 diagnostics
```

help lists commands; version queries application/core packages; status reads LightDM/fixed updater system units; logs returns only specified process-log tails from the latest three run directories; diagnostics returns fixed kernel/storage/linuxcnc-process information. No arbitrary paths, editing, upload/SFTP/SCP, TTY, port/X11 forwarding, or sudo. Reject arbitrary shell commands and extra arguments.

Maintenance status does not read the control socket and cannot prove idle. Future ordinary upgrades are requested by GUI through fixed root updating; maintenance accounts do not pull source, build, or install packages.

## Pre-update backup and manual recovery boundaries

After normal launcher shutdown and confirmed control socket/native-lock disappearance, root updating executes fixed `betterlinuxcnc-appliance backup` before apt. Failure blocks installation, displays an error, and leaves control stopped; never skip backup or restore old content automatically.

For a separate backup, first stop normally and run in the retained trusted root session:

```sh
betterlinuxcnc-appliance backup
```

No arbitrary paths are accepted. Snapshots live at root-only `/var/lib/betterlinuxcnc/recovery/snapshots`. Scope: `/etc/betterlinuxcnc`, mutable parameters/tool tables/positions in `/var/lib/betterlinuxcnc/machine`, and tool-managed fixed LightDM/X11/logind/SSH/sudo/Polkit/SysRq policies. Manifests record SHA-256, application version, and creation time. Clean older snapshots only after successful new creation/verification, retaining three.

Snapshots exclude large program libraries, CAM inbox, logs, cache, passwords, SSH private keys, and full-system images. They differ from activate's original-login-policy manifest and never automatically import/restore configuration. Controlled administrators verify versions, hashes, and onsite state before deciding restoration. Fixed `cnc-maint` commands provide neither backup download nor restore.

Snapshots share the system disk with source data and cannot prevent disk damage/loss. Onsite management must separately preserve required programs, credentials, and off-disk backups. This is not proof of disaster recovery or machine acceptance.

## Acceptance-record boundaries

### Read-only three-axis switch measurements, 2026-10-26

The user pressed switches manually while existing-system `halcmd getp` sampled read-only about every 100 ms. No target files, HAL wiring, or enable state changed; no motion commands were sent. Initial native state was emergency stop and disabled.

| User-confirmed physical axis | Raw input | Released | Pressed | Observed hold time |
| --- | --- | --- | --- | --- |
| X | `hm2_7i92.0.gpio.020.in` | FALSE | TRUE | About 1.34/1.44 s twice, then 6.91 s |
| Y | `hm2_7i92.0.gpio.021.in` | FALSE | TRUE | Six consecutive holds, about 1.34–2.79 s |
| Z | `hm2_7i92.0.gpio.022.in` | FALSE | TRUE | About 1.03/1.96 s twice |

All sampled holds remained stable and returned FALSE on release; quick taps were also captured. The user confirmed Y, final X, and previous two Z physical labels. This supports `.in` as active-high input for this target; 100 ms sampling cannot measure shorter mechanical bounce or replace debounce verification.

At that time, old `joint.0/1/2.home-sw-in` and X-negative/Y-positive/Z-negative limits remained FALSE without GPIO signal writers. Thus sampling verified switch-to-card inputs/mapping, not LinuxCNC limit responses or homing motion. The user later supplied X/Y/Z travel 420/275/90 mm for full migration. Wiring/homing modules still require PR/CI/Release deployment; travel input/software tests are not onsite motion acceptance.

Separately record release commit/package hash, installed version, configuration/data retention, account/file permissions, positive/negative SSH results, dedicated session, logs, and read-only control connectivity. Coordinates, axis count, homing flags, and program text in both layouts must match actual state.

Passing package/login isolation/read-only status checks does not establish home, jog, spindle, tool-change, or machining acceptance. Accept program loading, interpreter preview, and machining separately; local operators confirm actual actions. Disconnect never replays commands; the service stops only its session's jogging and cancels unsent steps, without aborting already-running programs.
