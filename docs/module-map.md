# Module responsibilities and directory map

2026-10-25: project-owned applications were consolidated under `app/` by responsibility; HAL and device drivers returned to upstream physical paths under `src/hal/`. Module build manifests declare languages. Python package names, Rust crate names, control protocols, and installed commands remain compatible. See root [AGENT.md](../AGENT.md).

2026-10-27: CAM communication, application updating, and Mesa updating now live under `app/platform/`. This groups platform capabilities without changing installed commands, systemd units, protocols, or privilege boundaries. Python control, Qt backend, and launcher ownership are unchanged. Configuration management is planned separately; no configuration-write interface is added by this move.

## Source ownership

```text
CMakeLists.txt               Product application build/test/install/package composition
cmake/ApplicationInstall.cmake Default /usr and lib installation layout
app/
  desktop/                   PySide6 + QML desktop
    app/                     GUI startup
    python/bettercnc/         desktop adapter and session Unix client
    qml/BetterCnc/            Ui, Catalog, Manual, Toolpath, Program, Chrome
    tests/                   QML public UI and Python public-interface tests
  controller/                Python controller, machine rules, isolated interpretation preview
    src/                     Public service, controller, preview packages
    tests/                   Control, protocol, file, preview verification
  platform/                  Rust platform capabilities; independent processes and permissions
    cam-link/                CAM network service
      src/cam_link/          TCP/UDP, inbox, state, job, jogging adapters
      tests/                 Real CLI and Python Controller cross-process tests
    updater/                 Release download/validation and fixed root update
    mesa-update/             Mesa manifest checks/download and root flashing gate
  launcher/                  Python orchestration, readiness, supervision
    src/bettercnc_launcher/  Configuration, processes, public protocol adapters
    tests/                   Installed CLI, process, socket boundaries
tools/
  diagnostics/               Independent Rust v1 compatibility diagnostics
  appliance/                 Explicit accounts/directories/login and fixed read-only SSH entry
  mesa-homing/               Fixed HOMEMOD build/public API verification adapter
vendor/cnc-mesa/              Immutable paired official Release snapshot and SOURCE.json
src/                         Native LinuxCNC source and unified build entry
  emc/                       Task, interpreter, motion, planning, kinematics, interfaces
  hal/                       HAL core, components, bindings, tools
    drivers/                 Mesa, GPIO, board and firmware resources
    user_comps/              Modbus, VFD, USB handwheels and other user-space components
  libnml/                    NML, mathematics and support
  rtapi/                     Real-time runtime adaptation
configs/                     Machine and example configurations
lib/, share/, tcl/           Upstream runtime/tools
tests/, unit_tests/          Native tests
docs/                        Project and upstream documentation
.github/ci/                  Module build/test entries
.github/workflows/ci.yml     Module CI and CI Gate
.github/workflows/release.yml Official DEBs for merged main PRs labeled build-release
```

Organize internals by function/device/bus, adding platform/CPU directories only for actual differences. Keep mixed-language components intact: HAL C++ bindings/Python generators belong to HAL; desktop C++ UI-test launcher belongs to desktop. Root language-based modules are no longer maintained.

## Communication and dependencies

Existing control chain:

```text
QML feature modules
  → bettercnc.desktop: PySide6 QObject, read-only snapshots and user operations
  → bettercnc.session: v2 Unix socket
  → betterlinuxcnc_service: session ownership, serial commands, preview process scheduling
      → bettercnc_controller.Controller: LinuxCNC API, machine rules, file writes
      → bettercnc_preview: separate process invoking LinuxCNC gcode extension
  → LinuxCNC C/C++ core: NML, Task, interpreter, real-time motion
  → HAL and C/C++ device drivers
```

`tools/diagnostics → Unix socket → Python v1 health` is independent diagnostics, without control sessions, v2 replacement, or actual-connectivity determination. Qt machine control does not pass through Rust; updating separately uses a Rust CLI, without merged protocols/new FFI.

CAM generates G-code on another device and sends it via TCP 6522 to Rust `betterlinuxcnc-cam-link`. protocol defines frames; inbox validates/saves files; transfer owns file-only upload lifecycle; homing submits independent homing; wf-transhoming.rs submits machining after homing. feedback returns state; control adapts v2 Unix; manual manages jogging leases; session composes connections/subscriptions; discovery owns UDP 8421. auto-run requires explicit start; upload never triggers motion. One Python Controller owns ordering, interlocks, cancellation, and persistence; duplicates/restarts do not replay. See [CAM protocol](cam-link-protocol.md).

Without a known machine IP, explicitly enable UDP discovery: machine broadcasts ANNOUNCE, CAM responds DISCOVER_REPLY, machine returns DISCOVER_ACK. CAM uses packet source IP, connects to the advertised TCP port, and authenticates. Rust discovery owns messages; the root entry owns lifecycle. Discovery grants no file/machine permission.

| Owner | Public entry | Boundary |
| --- | --- | --- |
| Qt UI | Public types in BetterCnc.<Capability> qmldir | No direct sockets, files, processes, hardware |
| Qt Python | bettercnc.desktop, bettercnc.session, bettercnc.__version__ | desktop uses public session/version; session standard library only |
| Startup | bettercnc_launcher.main, betterlinuxcnc-launch | Standard library; installed CLI/read-only v2, no service/machine internals |
| Rust socket | src/lib.rs | Diagnostics query/data only; private transport |
| Python service | betterlinuxcnc_service, Controller, StatusReader, bettercnc_preview | Public controller/preview collaboration, no reverse dependencies; StatusReader read-only |
| Rust system service | betterlinuxcnc_services::run, betterlinuxcnc-cam-link | Independent network/inbox binary; public Unix control only |
| Release updater | betterlinuxcnc-updater CLI | Qt JSON-lines requests fixed unit; root downloads/verifies without user paths/URLs/commands |
| Mesa updates | betterlinuxcnc-mesa-update, betterlinuxcnc-mesa-flash CLIs | Separate download/root flashing; no updateable bitstream this version, writes rejected |
| Appliance configuration | betterlinuxcnc-appliance | postinst only provisions; explicit plan/stage/prepare/activate; ordinary updates preserve login policy |
| SSH maintenance | cnc-maint fixed ForceCommand | help/version/status/logs/diagnostics only; no shell, arbitrary paths, forwarding, uploads, elevation, machine commands |
| HAL/drivers | Existing HAL/RTAPI | Device/signal adaptation, no dependency on new desktop/service |
| Native core | Existing EMC/NML/RTAPI | Retains real-time responsibilities and mixed-language link boundaries |

`app/platform/updater/` independently owns Release updates. Qt submits argument-free installation; root validates the package/machine state, normally stops linuxcnc user services, and backs up configuration/data. Backup failure prevents installation. The updater uses public read-only status, without control sessions; application version/install rules are in [application updates](firmware-updates.md).

LinuxCNC owns interpretation, interpolation, and real-time control. Desktop/transport perform no servo-cycle work. Sending is not completion; reconnect never replays. See [local control protocol](local-control-protocol.md) for units/lifecycle. Implementation/tests do not establish actual machine, INI/HAL, or target graphics acceptance.

## Build and delivery

Root CMake combines applications/appliance tools, each owning its install rules. It does not compile/install the native core. The user currently prohibits local/target builds and source tests, including Docker. CMake/CTest, Rust, and Python verification runs only in GitHub CI; target downloads completed DEBs. Public Python APIs/IPC remain the boundaries; build aggregation grants no private cross-module access.

Official DEBs additionally enable BETTERCNC_BUILD_MESA_HOMING=ON. tools/mesa-homing/build.py generates LinuxCNC 2.9.10 headers/halcompile in temporary source copies, then compiles fixed vendor zhulong_homing, not the full core. Ordinary Qt/launcher checks disable this by default. Install only `/usr/lib/linuxcnc/modules/zhulong_homing.so` and `/usr/share/betterlinuxcnc/homing/provenance.json`, without replacing other native modules. SOURCE.json pins vendor per-file/archive hashes, source commit, and release-manifest hash; do not edit vendor in place.

Twenty-seven public API software scenarios use the same generated headers; separate CI runs original vendor generator regressions/GHDL simulation. Generator/simulation/ELF/20-symbol checks are not board acceptance. Application packages support existing LinuxCNC 2.9 systems, but HOMEMOD supports only upstream 2.9.10; explicit enablement verifies actual dpkg core version. Debian 13 default 2.9.4 is used only for package lifecycle checks, not module loading. Unknown total travel stays inputs-only without HOMEMOD/HOME.

Application `26.10.26.1` is independent of native VERSION. Official artifact: betterlinuxcnc-qt_26.10.26.1_amd64.deb, tag v26.10.26.1, Release demo v26.10.26.1. It includes four Rust binaries for CAM, application updates, and two Mesa CLIs, installed through apt/dpkg. Desktop-only CMake installs GUI only; system-service-disabled builds are split validation only.

Application code: /usr/lib/betterlinuxcnc and /usr/share/betterlinuxcnc. Configuration: /etc/betterlinuxcnc. Programs/inbox/mutable state: designated /var/lib/betterlinuxcnc children. Data/cache roots remain root-owned; operator HOME is /var/lib/betterlinuxcnc/home, cache /var/cache/betterlinuxcnc/user, logs /var/log/betterlinuxcnc/launcher. Updates preserve onsite data/configuration; initial migration/isolation is explicit. See [local connection guide](linuxcnc-local-connection.md).

The native core retains src/Makefile and existing Meson builds. src/hal/, src/hal/drivers/, and src/hal/user_comps/ are real directories; Make scanning needs no cross-root links. CI archives cover physical files and test unstaged migrations; upstream resources/configurations remain part of the complete repository.

HAL tools and src/rtapi/uspace_rtapi_app.cc retain legacy private-header access as native-runtime collaboration, with exceptions in module AGENTS. Directory cleanup does not expand private-header exposure.

## CI entry points

- `.github/ci/check-source.sh`: workflows, shell, Python syntax, AXIS removal, directory migration.
- `.github/ci/native-check.sh hal|motion|drivers|task|interpreter|python-extensions`: six independent native build/checks without controller/simulator/real-time/hardware startup.
- Independent mesa-homing job: shared native dependency headers, fixed module and 27 API scenarios, generator regressions/GHDL; no module loading/hardware.
- `.github/ci/python-check.sh service|preview|desktop|launcher`: current-source packages/public interfaces; preview requires real gcode.
- Independent appliance-checks (3.11/3.13): Ruff/format/public CLI, including migration, preservation, SSH restrictions; root CTest also registers appliance-provisioning.
- `app/desktop/scripts/ci-check.sh --suite desktop|qml`: Python desktop versus QML; no arguments runs all Qt checks.
- tools/diagnostics/, app/platform/cam-link/, app/platform/updater/, app/platform/mesa-update/: cargo fmt --check, cargo check --locked --all-targets, cargo clippy --locked --all-targets -- -D warnings, cargo test --locked. Cross-process tests need Python 3.11+, selectable by SERVICE_TEST_PYTHON.
- `.github/ci/check-configs.py` and config-tests/: HAL/INI/Tcl static syntax, local references, include cycles.

Debian deb-package builds real DEBs in GitHub, accepts first/repeated installation and explicit policy activation, and checks actual sshd/visudo output without SSH/display manager/LinuxCNC/hardware startup. Targets install CI artifacts only; package acceptance joins CI Gate. Dependency/test-wheel installation remains isolated to CI.

Release workflow publishes only merged main PRs with build-release, passing same-merge-SHA main push CI Gate and unique DEB. Only publishing writes repository contents. Verify hash/version/architecture/source/tag and paired same-tag CNC-Mesa manifest/commit/archive hashes, then publish latest with original mesa-release.json and CNC_MESA_PAIR.json. Missing pairs fail closed and may be retried from main with the same merged PR. No SSH deployment; source archives are not DEBs.

README maintenance remains manual. Directory-migration README ownership changes were authorized, but text remained unchanged. Old service paths in root README, Python-service README, src/README.md, and src/emc/usr_intf/python-interface/README.md still await manual updates; this map is authoritative for current entries. Historical paths are not current entry points.

English companion translations of the checksum-pinned vendor documents are available in [Mesa homing](cnc-mesa-homing.en.md) and [LinuxCNC integration handoff](cnc-mesa-linuxcnc-integration-handoff.en.md). Original vendor snapshot bytes remain unchanged.
