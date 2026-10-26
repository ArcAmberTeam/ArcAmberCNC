# Vue to Qt Quick/QML migration and control integration

The native QML UI was introduced on 2026-10-02, retaining Vue layout, assets, Chinese copy, action IDs, shortcuts, and panel interactions. Vue/Web, Tauri, and deployment scripts were removed on 2026-10-08; historical Web material remains in Git. On 2026-10-25, responsibility-based organization moved the desktop to `app/desktop/` and independent Rust v1 diagnostics to `tools/diagnostics/`. The user requested complete operations, explicitly using Unix sockets first and no simulator.

The current chain is **QML → PySide6 QObject → Unix socket → independent Python service → LinuxCNC**. Qt does not import LinuxCNC; the service does not depend on Qt. PySide6 replaced the initial C++ application launcher; only the Qt Quick Test launcher remains C++. Pages are native QML without WebView. LinuxCNC retains G-code interpretation, interpolation, motion planning, and real-time execution; Python adapts control and schedules isolated previews.

## Module boundaries

| Public entry point | Responsibility |
| --- | --- |
| `bettercnc.desktop` | QML engine, read-only snapshots, program documents, desktop file dialogs, history, explicit tool startup |
| `bettercnc.session` | v2 Unix socket client; reconnect reads state without resending commands |
| `betterlinuxcnc_service` | Private socket, sole session owner, command thread, jogging leases, preview subprocesses |
| `bettercnc_controller.Controller` | LinuxCNC stat/command/error channel, configuration, operation conditions, acknowledgements, program/tool-table writes |
| `bettercnc_preview` | Subprocess LinuxCNC `gcode.parse`, isolated parameter copies, millimeter segments |
| `BetterCnc.Ui`, `BetterCnc.Catalog` | Shared styles, controls, menu metadata, local assets |
| `BetterCnc.Manual`, `Toolpath`, `Program` | Observe injected public data, emit operation intent, retain presentation state |
| `BetterCnc.Chrome`, `Workspace.qml` | Menus, dialogs, shortcuts, feature composition |

Python cross-module imports use public package entry points; QML uses public `qmldir` types. `app/desktop/scripts/check_boundaries.py` checks both. Preview processes may use **read-only** `linuxcnc.stat().poll()` to initialize LinuxCNC 2.9 tooldata mappings; only Controller holds command/error channels. This vendor initialization supports independent interpretation and never permits preview machine commands.

## Integrated behavior

- Real connection, emergency stop, power, modes, joint/axis, homing state, actual/commanded positions, offsets, overrides, spindle, coolant, active G/M codes, and errors.
- Emergency stop, power, home/unhome, joint/world mode, continuous/incremental jogging, MDI, spindle/brake, coolant, overrides, velocity limits, and work/tool touch-off.
- Program open, reload, edit/save, run, run from selected line, step, pause, resume, stop, optional stop, and block delete. Service saves only after checking fresh idle state; displayed and controller-loaded files must match before running.
- Tool-table display, edit/save, and reload. Save paths come from actual service INI; format validation is server-side. Editing is limited by a single 64 KiB protocol frame; large files may still open from disk but must not be truncated on save.
- Interpreter segments, execution lines, projection switching, zoom, actual traces, coordinate systems, and units. Offline shows unknown state, never demo coordinates or illustrative toolpaths.
- HAL configuration, meters, scopes, and similar menus explicitly start installed local LinuxCNC tools; missing/unconfigured tools produce explicit errors.

Capabilities drive UI availability; the service rechecks conditions before execution. Command acceptance and LinuxCNC acknowledgement remain distinct. See [local control protocol](local-control-protocol.md) for protocol, units, and connection lifecycle.

## Startup

See the [LinuxCNC local connection guide](linuxcnc-local-connection.md) for target GUI/service synchronization, read-only diagnostics, and switching steps.

Target environment: Debian 13, Qt/PySide6 6.8+, Python 3.11+, and installed LinuxCNC 2.9. The `.deb` installs GUI and independent service launchers, declares runtime dependencies, and installs user-service/session entries. The launcher starts LinuxCNC using existing configuration without rewriting INI/HAL.

Alongside a LinuxCNC session already started by the user, run separately as the same system user:

```sh
betterlinuxcnc-service --ini /absolute/path/machine.ini
betterlinuxcnc --ini /absolute/path/machine.ini
```

Default endpoint: `$XDG_RUNTIME_DIR/betterlinuxcnc/control.sock`, or `/tmp/betterlinuxcnc/control.sock` if no runtime directory is set. Both commands may receive the same `--socket /private/directory/control.sock`. The current user must own the 0700 parent; socket mode is 0600. Qt `--ini` (also accepting LinuxCNC's `-ini`) requires matching service configuration; it does not start the service or switch machine configuration.

On closing, Qt requests stopping its jogging and cancels unsent operations/preview; the service stays independent. It does not automatically stop already-running machining. As LinuxCNC DISPLAY, the actual startup configuration determines how its exit affects the entire LinuxCNC lifecycle; do not assume permanent background operation.

Run from source, with LinuxCNC extensions from the target-matching system installation:

```sh
PYTHONPATH=app/controller/src python3 -m betterlinuxcnc_service --ini /absolute/path/machine.ini
python3 app/desktop/app/main.py --ini /absolute/path/machine.ini
```

For macOS UI development, create `python3.12 -m venv app/desktop/.venv`, install `PySide6==6.8.3`, and run `app/desktop/.venv/bin/python app/desktop/app/main.py`. Without LinuxCNC, retain the offline UI rather than simulating the machine.

## Build and checks

In an environment with Qt development tools and PySide6:

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

On macOS add `-DCMAKE_PREFIX_PATH="$HOME/Qt/current/macos"` and `-DPython3_EXECUTABLE="$PWD/app/desktop/.venv/bin/python"`. Use separate build directories per platform.

Complete Debian 13 CI entry:

```sh
docker run --rm --init --platform linux/amd64 \
  --mount "type=bind,src=$PWD,dst=/workspace" --workdir /workspace \
  -e QT_BUILD_DIR=/workspace/build-debian \
  debian:13-slim bash app/desktop/scripts/ci-check.sh --install-deps
```

The script installs container dependencies, builds, and runs UI/Python/socket/interpreter tests without creating release packages or deploying to the target. offscreen/software is for CI only; normal operation uses target desktop graphics. Service and Qt desktop also provide separate wheel/sdist builds; the service wheel does not embed native LinuxCNC extensions.

GitHub workflow remains `.github/workflows/ci.yml`: `qt-build` separately checks the Python UI backend and QML, Python 3.11/3.13 jobs verify the service package, and Rust jobs verify the independent socket library. Retain six native-module checks, real interpreter preview, and HAL/INI/Tcl configuration checks. Web/Tauri and deployment jobs were removed; CI only builds, tests, and uploads diagnostics.

## Verification limits

As requested, no simulator or real machine was started. Control tests use vendor substitutes through public Controller to check calls, conditions, and sequences; socket tests use real local connections. Geometry tests invoke Debian LinuxCNC's real `gcode` extension, with required state initialization substituted for machine-free tests. These do not establish actual NML, homing, tool changes, hardware actions, or target INI acceptance.

Preview is not full machining simulation: it displays XYZ tool-tip segments; rotary axes participate in coordinate data without a physical machine kinematics/collision model. Python REMAP, probing, and execution-dependent user code must not produce misleading previews. INI files containing `#INCLUDE` require an expanded version. Parameter writes affect temporary copies only. Defaults limit programs to 32 MiB, 200,000 segments, and 20 seconds of interpretation, plus an overall service process timeout; limit/interpretation errors display explicit reasons.

External inputs such as M66 receive preview values from LinuxCNC's preview interpreter; input-dependent branches may differ from actual execution. After saving tool touch-off, existing nonzero tool-length compensation is explicitly reloaded with G43 for the current tool number, replacing dynamic G43.1/G43.2 or other H compensation. Existing G49 does not automatically enable compensation. The UI explains this before submission.

GUI heartbeat and the service's 600 ms jogging lease provide software disconnect protection. Native LinuxCNC commands may await NML acknowledgement while holding Python's GIL; stop requests may wait until the call returns. The lease is not a hard real-time shutdown guarantee. Physical safety chains remain the machine system's responsibility.

Chinese fonts, scaling, minimum windows, dialogs, release/focus-loss behavior, and actual INI/HAL sessions on Debian 13 Intel graphics still require onsite acceptance. Local screenshots cannot establish identical pixels across rendering stacks. README maintenance remains manual.
