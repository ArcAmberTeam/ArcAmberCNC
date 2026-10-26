# Native Qt Quick UI rules

First follow the root [AGENT.md](../../AGENT.md). `app/desktop/` is the native desktop entry point, using PySide6, Python 3.11+, CMake, and Qt 6.8+; C++17 is used only for the UI test launcher. The Web UI and Tauri desktop environment have been removed. Organize this directory by capability first, adding platform/CPU layers only for actual differences.

## Modules and public entry points

- `app/` owns only application startup and QML engine setup. `qml/Main.qml` and `qml/Workspace.qml` compose the window and feature modules without owning machine rules.
- `qml/BetterCnc/<Capability>/qmldir` declares public module types. Cross-module access uses `import BetterCnc.<Capability> 1.0`; do not bypass entry points through relative paths, JavaScript files, or `internal` types.
- `Ui` owns colors, fonts, icon drawing, and generic controls. `Catalog` owns menu/toolbar metadata, Chinese copy, and attributed assets. Neither depends on feature modules or on the other. Historical examples must not become production state.
- `Manual` owns manual/MDI controls, axis selection, and overrides. `Toolpath` displays service-interpreted segments, actual traces, and coordinate readouts. `Program` displays actual program text, selected lines, and execution lines. These three depend only on `Ui` and `Catalog` and observe machine/program state through injected public data interfaces.
- `Chrome` owns menus, toolbars, and information dialogs. It may depend on `Ui`, `Catalog`, and public presentation interfaces of `ManualState`/`ToolpathState`, but must not import other feature panels or private types.
- `Workspace` assembles feature panels, shared presentation state, and shortcuts. Do not introduce global `utils`, `stores`, `shared`, universal action dispatchers, or machine-state dumping grounds. Module dependencies must be acyclic.
- Maintain CMake resource lists, `qmldir`, and `scripts/check_boundaries.py` together. Define ownership/dependencies before adding a module, then update checks; do not suppress violations with ignore rules.
- Python public entry points are `bettercnc.desktop`, `bettercnc.session`, and application metadata `bettercnc.__version__`; underscore-prefixed files are private. desktop imports only session/version public entry points across modules; session uses only the standard library. The Qt process must not import `linuxcnc`, `gcode`, `hal`, or service packages in `app/controller/`.

## Presentation and system boundaries

- Use the [platinum UI specification](../../docs/qt-platinum-ui.md) and centralized variables in `Ui/Theme.qml`. Preserve action IDs, shortcuts, focus, and editable-input behavior. Adjust visuals/layout to explicit user requirements and accept large windows, compact breakpoints, and minimum windows.
- `ManualState`, `ToolpathState`, and component properties store only presentation state. Coordinates, spindle, and execution state come from read-only service snapshots; issuing a command does not mean it completed.
- `DesktopBackend` receives state and submits commands through a socket client on a dedicated QThread. The desktop does not start LinuxCNC or the Python service. Jogging uses GUI heartbeat, service leases, and stop on release/focus loss. Reconnection restores state reads only, never command replay.
- QML components must not directly access platforms, networks, files, processes, or LinuxCNC. The desktop may read program files; program/tool-table writes require service validation against fresh state. The independent service retains rules and the sole command writer; LinuxCNC retains real-time responsibilities.
- Qt uses the existing Python v2 control session. Independent `tools/diagnostics/` retains v1 `health` diagnostics and is not connected to Qt. Represent service reachability and machine connectivity separately.
- Serve all static assets locally, preserving licenses/attribution. Do not load CDNs, external fonts, or telemetry. The service interprets toolpaths in a separate process and sends bounded pages; geometry layers must not redraw completely on every coordinate snapshot.

## UI and connectivity conventions

- The primary target window is 1024×600. Retain guided hobbyist and professional layouts, reusing machine operations/state through public modules. Put infrequent options on a settings page filling the application window; keep common actions, emergency stop, and stop on the main screen. The compact header omits BetterLinuxCNC branding; the window title shows the program filename or “No program open.”
- 3D rotation, panning, zoom, and view settings change presentation only. Touch jogging starts on press-and-hold and stops on release, drag cancellation, focus loss, or hiding. Preview keyboard input must not trigger machine jogging/homing shortcuts. Continue checking touch targets and minimum windows after layout changes, not large screens alone.
- Official entry points are `app/main.py` and installed `betterlinuxcnc`, both using the real service. `--check-connection` makes a read-only query through `bettercnc.session.read_machine_status`, without a window or control rights. Exit 0 means machine connected, 2 means service reachable but machine offline, and 1 means endpoint/transport/protocol error. Do not combine it with `--ini` or `--program`.
- `--kiosk`/`BETTERCNC_KIOSK=1` runs the dedicated fullscreen operator UI without controls to exit to an ordinary desktop. `--kiosk-status` is a separate startup-status page without a control backend or machine connection; the launcher manages its lifecycle through the public CLI. Installed version comes from `bettercnc.__version__`, not LinuxCNC core `VERSION`.
- Application updates use the independent `betterlinuxcnc-updater` CLI JSON-lines interface. Qt may request only argument-free `install` and cannot pass package paths, URLs, versions, or commands to root. Program selection is confined to configured program/inbox directories. QML must not operate platform file pickers or external editors itself.
- Mesa updates display through independent `betterlinuxcnc-mesa-update status|check` JSON. Present these separately from application DEB updates. UI checks do not download, stop control, or flash; source releases without a verified bitstream must explicitly show no firmware. A system timer owns periodic checks; the GUI reads status infrequently. Future verified bitstreams paired with the installed version may explicitly request maintenance through separate argument-free `betterlinuxcnc-mesa-flash request`. The root service owns independent verification, shutdown, backup, flashing, and readback gates. A request is not completion; the UI passes no URL, file, board address, or command.
- Interactive tests without LinuxCNC use `app/desktop/tests/interactive/main.py`, currently only in permitted remote validation environments. Inject vendor interfaces externally while reusing the production GUI/service. Do not add fake state or simulation switches to production. Both Controller and StatusReader must receive the same test device.
- `external-interface-integration` is registered in CTest, covering original GUI/service end-to-end behavior, read-only diagnostics coexisting with an active control session, and disconnect recovery. Substitute tests do not establish real-interpreter or motion acceptance. See the [local connection guide](../../docs/linuxcnc-local-connection.md) for actual target installation/display acceptance records.

## Verification and CI

- After changes, run CMake configure/build, CTest, and affected-QML qmllint only in GitHub CI. The user prohibits local/target builds and source tests, including local Docker. Targets only install complete CI DEBs and perform actual runtime acceptance. Tests use public modules and observable UI, not cross-module internal imports.
- When creating/changing dependency rules, temporarily add an illegal import, confirm failure, remove it, and confirm valid code passes.
- Public UI tests observe behavior through `objectName`, keyboard, and mouse input. Python tests use public interfaces and real Unix sockets with controlled service substitutes. Do not expose private internals for testing or start simulators/machines.
- macOS builds and headless tests cannot replace Debian 13, Intel integrated graphics, Chinese font, scaling, and window lifecycle acceptance. Container builds do not verify target graphics or the machine.
- `.github/workflows/ci.yml` separately displays “Python: Qt UI backend” and “QML: Qt desktop UI.” `scripts/ci-check.sh --suite desktop` verifies the installed Python package; `--suite qml` runs QML, module-boundary, and startup checks. Without `--suite`, the full suite still runs. The desktop suite installs test wheels only in isolated environments; root builds and a separate CI job own the official DEB. Release rules follow root AGENT and do not deploy to the target.
- See the [Qt migration notes](../../docs/qt-qml-migration.md) for build, startup, and acceptance steps. All Markdown follows the protection rules below.

## Reading and protected documentation

Follow the root [AGENT.md](../../AGENT.md) and every ancestor directory guide. Before implementation, read every Markdown file in this directory and each affected child directory, plus the relevant linked interface contracts. Inspect existing code and dependencies before choosing a location or library.

This guide and all other Markdown are protected: AI must neither change them autonomously nor proactively propose changes. An explicit human request and a second confirmation of the intended scope are required before any write. Keep documentation and explanatory comments English; never append change records, progress reports, operational logs, email addresses, key material, or credentials.

Extend an existing class/module when the new behavior belongs to it. Add a focused file/directory only for a distinct responsibility, lifecycle, interface, or privilege boundary. Reuse verified public APIs; do not invent dependencies, duplicate rules, or import sibling private internals. In long source files, bracket substantial feature-owning classes with the language-appropriate English BEGIN/END markers defined in root AGENT.md. Builds and source tests run only in GitHub CI.

## Child directory guides

- [app/AGENTS.md](app/AGENTS.md): Own the thin executable wrapper and Python startup entry for the Qt desktop.
- [python/AGENTS.md](python/AGENTS.md): Contain the installed bettercnc package and its public presentation and transport boundaries.
- [qml/AGENTS.md](qml/AGENTS.md): Own Main, Workspace, guided/professional layouts, settings pages, file-selection presentation, and the standalone kiosk-status screen.
- [scripts/AGENTS.md](scripts/AGENTS.md): Own the desktop/qml CI entry script and static dependency-boundary checker.
- [tests/AGENTS.md](tests/AGENTS.md): Own the Qt Quick Test launcher, public QML behavior tests, controlled backends, and visual-preview support.
