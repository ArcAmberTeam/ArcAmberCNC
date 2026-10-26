# Application Release updates

Update Firmware under Settings → About checks the latest official GitHub Release of `ArcAmberTeam/ArcAmberCNC`, downloads the application package for the current Debian architecture, and verifies it. This updates GUI, controller service, CAM, launcher, updater, and appliance tools, not control-card/motor firmware or the source workspace. The native LinuxCNC core remains managed separately by system package `linuxcnc-uspace`.

## 26.10.26.5 release conventions

| Item | Current convention |
| --- | --- |
| Release name | `demo v26.10.26.5` |
| Tag | `v26.10.26.5` |
| Debian Package / Version | `betterlinuxcnc-qt` / `26.10.26.5` |
| amd64 package | `betterlinuxcnc-qt_26.10.26.5_amd64.deb` |
| Checksum asset | `SHA256SUMS`, each filename appearing once |
| Pairing assets | Same-tag CNC-Mesa `mesa-release.json` and this repository's `CNC_MESA_PAIR.json` |
| Release type | Official, non-draft, non-prerelease, marked latest |

`demo` in the name does not change release type. The updater reads `/releases/latest`, not a name-selected version. Removing tag prefix `v` must produce the exact `.deb` Version. Filename architecture, package architecture, and `dpkg --print-architecture` must match; same-version installs and downgrades are rejected.

Root CMake, desktop Python package, and public `bettercnc.__version__` share the application version. Root `VERSION` value `2.9.10` is the LinuxCNC core version; Rust crate versions also cannot determine application update eligibility.

The same-version `ArcAmberTeam/CNC-Mesa` Release supplies source/integration material. Its manifest fixes `schema_version=1`, `board=zhulong-v2`, and `variant=PIN_ZHULONG_V2_34`; `version` and `compatible_app_version` are `26.10.26.5`. `source_commit` must match the tag target on that repository's `main`. Descriptive metadata may expand, but application, board, provenance, and verification claims must satisfy the release contract.

This version has `firmware.available=false`, null `asset`/`sha256`/`size`, and `origin=unavailable`. Nested `firmware.verification` fields `implementation`, `timing`, `board_approved`, and top-level `physical_constraints_verified` are false. Missing new ISE bitstreams do not prevent application release, but flashing is forbidden. Factory bitstreams in reference archives are not update payloads.

Independent `app/mesa-update/` installs Rust CLIs `betterlinuxcnc-mesa-update` for checks/status/download and `betterlinuxcnc-mesa-flash` for a separate fixed root-service entry. This version rejects actual flashing and has no generic Polkit grant. Checks run as `linuxcnc`; installation does not start the check timer or flash service. Application DEB updating and card flashing have separate permissions, state, and failures.

The paired integration archive is an immutable `vendor/cnc-mesa` snapshot. `SOURCE.json` records Release, source commit, archive/manifest hashes, and per-file hashes. Release gates compare the remote manifest with the exact snapshot compiled by the application, not version alone. Packaged `zhulong_homing.so` is a LinuxCNC HOMEMOD software module, not FPGA firmware; it may be enabled only with upstream core 2.9.10. Explicit `prepare` verifies core/development package versions, headers, and module hashes. The user confirmed XYZ-only hardware; the three-axis option strictly removes reviewed reserved ABC configuration. X/Y/Z total travel 420/275/90 mm is input only for this machine's full migration. Unknown travel uses inputs-only. Installation/updates do not automatically load the module or trigger HOME. See [explicit staging, preparation, and activation](linuxcnc-local-connection.md#explicit-staging-preparation-and-activation) for commands and onsite acceptance boundaries.

Each package requires a valid Release-asset `sha256:` digest or a unique corresponding entry in that Release's `SHA256SUMS`. Download URLs are restricted to the current repository and HTTPS throughout. Missing Release, architecture mismatch, multiple candidates, or invalid versions/checksums produce UI explanations and preserve the installation. This feature does not create/publish Releases.

## Fixed system-service installation boundaries

Qt calls only `betterlinuxcnc-updater fetch --current-version <version>`, `status`, and argument-free `install`, observing JSON lines. It cannot attach package paths, URLs, target versions, sockets, or arbitrary commands to install requests.

1. The ordinary user checks/downloads into private cache; the UI shows progress/verification. After download, the user may request Install and Restart.
2. `install` permits only configured `linuxcnc` to request fixed `betterlinuxcnc-system-update.service`. Polkit permits starting that unit only, without general systemd, pkexec, or sudo access; do not use a generic administrator prompt to bypass limits.
3. The system unit runs fixed root `betterlinuxcnc-updater apply-system` and reads root-owned `/etc/betterlinuxcnc/updater.json`. It fixes `user=linuxcnc` and `config=/etc/betterlinuxcnc/launcher.json`; reject extra fields or other users/paths.
4. Root independently redownloads/verifies official Release content, never user-writable `.deb`, manifests, or environment proxies. Check package name/version/architecture/size/SHA-256 and stream-check Debian data/control archives, rejecting escaping paths, links, special files, unsafe permissions, non-root owners, and unknown control files. Only exact content/ownership/mode-matched fixed `postinst` for idempotent `provision` is allowed; reject other/altered scripts. The sole conffile is `/etc/betterlinuxcnc/updater.json`; existing install destinations must also be trusted.
5. Read fresh public `machine.status`. Unknown, enabled, paused, moving, spindle-running, or pending-task states block installation. Do not acquire control or send shutdown, homing, jog, or other machine commands.
6. After download verification, recheck state, stop the `linuxcnc` launcher user service normally according to its prior state, and confirm control socket/native lock disappear.
7. Root runs argument-free `/usr/sbin/betterlinuxcnc-appliance backup` for current configuration, mutable machine data, and fixed host policies. Startup/backup/verification failure prevents apt; preserve snapshots, keep control stopped, and report failure.
8. Only successful backup permits fixed `/usr/bin/apt-get --yes --no-remove install`; then verify dpkg's installed version. Restore the previously running managed launcher only on success. Failure leaves it stopped with a reason, never force-killing the core or starting mixed versions.

Dependencies include systemd user sessions, Polkit, apt/dpkg, and verifiable Debian packages; macOS previews cannot install. Root remains responsible for package management; operator/SSH maintenance accounts do not gain root shells. Packages provision accounts/directories while retaining passwords/data. Ordinary updates do not run `prepare`/`activate`, change login policy, or import machine configuration.

## Installation paths and retained data

| Path | Ownership and purpose |
| --- | --- |
| `/usr/bin/betterlinuxcnc*`, `/usr/sbin/betterlinuxcnc-appliance` | Root-owned installed commands |
| `/usr/lib/betterlinuxcnc`, `/usr/share/betterlinuxcnc` | Root-owned application modules/QML |
| `/usr/lib/linuxcnc/modules/zhulong_homing.so` | Sole additional native HOMEMOD; explicit enablement only for LinuxCNC 2.9.10 |
| `/usr/share/betterlinuxcnc/homing/provenance.json` | Module hash, build source SHA, core version/header hashes, vendor provenance, software scenarios |
| `/etc/betterlinuxcnc/launcher.json`, `machine/` | Onsite configuration from explicit migration; absent from application package |
| `/etc/betterlinuxcnc/updater.json` | Root-owned fixed updater configuration, Debian conffile |
| `/var/lib/betterlinuxcnc/{programs,inbox,machine}` | Programs, CAM inbox, tool tables/parameters/positions, writable by `linuxcnc` |
| `/var/cache/betterlinuxcnc/user/betterlinuxcnc/update` | User check/download cache, never root install input |
| `/var/cache/betterlinuxcnc/update` | Root-private downloads and `install.log` |
| `/var/lib/betterlinuxcnc/update/status.json` | Root-written, user-readable install status |
| `/var/lib/betterlinuxcnc/recovery/snapshots` | Root-private pre-update snapshots; retain latest three after successful creation/verification |
| `/var/log/betterlinuxcnc/launcher` | Launcher/child logs; updates do not clear history |

Top-level `/var/lib/betterlinuxcnc` and `/var/cache/betterlinuxcnc` always remain root-owned and unwritable by ordinary users; never give the whole tree to the operator. Ordinary users own only designated children. Examples install to `/usr/share/doc/betterlinuxcnc-qt/examples/launcher.example.json` without overwriting actual configuration.

GUI exit does not terminate the system updater; reopening reads public system status. Fixed `cnc-maint logs` reads only specified launcher process logs, not root-private updater logs. Controlled administrators diagnose installation failures through system journal/private `install.log`.

Pre-update snapshots cover `/etc/betterlinuxcnc`, parameters/tool tables and other data in `/var/lib/betterlinuxcnc/machine`, and tool-managed fixed host policies, recording SHA-256, application version, and time. They exclude large program libraries, CAM inbox, logs, caches, passwords, and SSH private keys. Rotate old snapshots only after successful new creation/verification; never delete backups and proceed after failure.

Backup does not automatically restore files, roll back packages, or change machine state. Controlled administrators review versions, hashes, and onsite configuration before restoring; see [backup and manual recovery boundaries](linuxcnc-local-connection.md#pre-update-backup-and-manual-recovery-boundaries). Same-disk snapshots cannot survive disk failure or replace program-data, credential, and separate-disk backups.

## Build, release, and verification

The user prohibits local/target builds, including local Docker. All compilation, source testing, and packaging run on GitHub-hosted runners. Targets download complete DEBs rather than building source. Entry points: `.github/workflows/ci.yml`, `.github/workflows/release.yml`, and `.github/ci/deb-package.sh`.

1. Subsequent application changes commit on existing `kihon` and merge through `kihon → main` PRs. Add `build-release` when release is required; unmerged/unlabeled PRs and other branches do not publish.
2. Module CI `deb-package` builds the complete package in Debian 13 amd64 and performs real first/repeated installation. Check accounts/directory permissions/password/data retention and actual isolated SSH/sudo policy without starting machines, graphics, or SSH services.
3. Success uploads `betterlinuxcnc-deb-<SHA>` containing actual `.deb`, `SHA256SUMS`, and `SOURCE_COMMIT`. `CI Gate` requires module tests and package acceptance.
4. Release workflow checks eligibility after main CI or labeling a merged PR, reading only successful main push CI and the unique artifact for the same merge SHA. Only publishing has repository-content write access; it does not check out/execute PR source.
5. Publishing rechecks source SHA, package name, four-part version, amd64, SHA-256, and tag target, then read-only checks same-tag official CNC-Mesa Release manifest hash, source commit, and source/integration archive hashes/sizes. Check before draft creation and before publication; missing/changed pairing prevents official release.
6. Success uploads `.deb`, `SHA256SUMS`, original-byte paired `mesa-release.json`, and `CNC_MESA_PAIR.json` containing both source commits, Release/asset IDs, and manifest hash. Publish `demo v26.10.26.5` as official latest. GitHub's automatic source zip/tar is not an install package.

Publish CNC-Mesa first, application second. Cross-repository access is public/read-only; no PAT or cross-repository write permission. If application CI finishes first, rerun the failed release job once its pair exists or manually dispatch from `main` with the original merged PR number. Retries still verify label authorization, same merge SHA, passing CI, and original artifact. Existing asset hashes must match; do not replace published files or let late older versions lower latest.

Official packages enable system services and include four real target-architecture Rust binaries: CAM, application updater, Mesa checks, and flashing gate. CI builds from that commit, not developer artifacts. `BETTERCNC_CAM_LINK_BINARY`, `BETTERCNC_UPDATER_BINARY`, `BETTERCNC_MESA_UPDATE_BINARY`, and `BETTERCNC_MESA_FLASH_BINARY` remain only for split CI verification. `BETTERCNC_BUILD_SYSTEM_SERVICES=OFF` test packages and standalone desktop installs are not official releases. CPack stages through `DESTDIR`; real install acceptance writes only into disposable CI containers.

Official packages also enable `BETTERCNC_BUILD_MESA_HOMING=ON`. The adapter generates headers/halcompile from repository 2.9.10 source, builds only the fixed module, and runs 27 public API scenarios. Package acceptance checks real ELF, 20 public symbols, and provenance. Debian 13's default 2.9.4 core is used only for application first/repeated installation, never module loading or an ABI compatibility claim. Verify actual target core/configuration separately.

Launcher staged-installation regression checks version, real binaries, configuration retention, systemd units, and DEB layout. Independent appliance CI covers migration rehearsal/maintenance restrictions; Rust updater CI covers real Debian archives and fixed postinst positive/negative cases. Release requires complete same-commit `CI Gate`. Pipelines publish install assets without connecting/deploying to the target.

Follow the [local connection guide](linuxcnc-local-connection.md) for installation, account migration, dedicated sessions, and connectivity acceptance. Package/read-only checks are not actual update, graphical-session, or motion acceptance; record these separately.

## v5 fixed machine migration and update repair

The package accepts only the captured, hash-matched installed v1 or v4 Zhulong profiles for the operator-authorized v5 migration. It requires the stack stopped, verifies the installed HOMEMOD ABI and provenance, then atomically exchanges the complete machine configuration. Unknown edits are rejected. Existing v4 motor mapping is retained, not swapped again. Work offsets, tool data and programs are preserved.

HOME remains zero, HOME_OFFSET remains -5 mm and MIN_LIMIT becomes -0.1 mm for XYZ. This prevents the observed -7.62939436e-8 mm numerical residue at HOME from triggering the negative soft limit, while keeping that limit 4.9 mm inside the home switch. MAX_LIMIT stays 410/265/80 mm. XYZ runs concurrently with search speeds 15/15/5 mm/s, independent first retreat 2 mm/s, latch 1 mm/s and final retreat 5/5/2 mm/s. The first test is explicitly restricted to a clear empty machine without a tool. Simulation does not establish physical collision clearance or braking performance.

The v4 fixed update unit retains CAP_SETUID/CAP_SETGID for its runuser transition under NoNewPrivileges. CI verifies this with actual systemd rather than a command stub. v5 also normalizes the package documentation root to root:root 0755, covering the legacy 0775 mode that previously caused secure package preflight to reject the destination. No general sudo grant is added.

The dedicated X11 session disables idle screensaver blanking and DPMS through the installed xset command. Regular desktop sessions are unaffected. This prevents idle display power-down; it is not evidence that GPU suspend/resume has been validated.
