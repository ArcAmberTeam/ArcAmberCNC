# LinuxCNC external-interface tests for the Qt GUI

Run from the repository root:

```sh
app/desktop/.venv/bin/python app/desktop/tests/interactive/main.py
```

No installation, startup, or connection to real LinuxCNC, HAL, virtual machines, or hardware is needed. This is a test-only entry point; production behavior is unchanged.

## Injection point

```text
Original qml/Main.qml (guided / professional layouts)
  → Original bettercnc.desktop.DesktopBackend
  → Private Unix socket (real v2 session, commands, preview pagination)
  → Original betterlinuxcnc_service.serve
  → Original bettercnc_controller.Controller
  → Test LinuxCNCInterface: stat / command / error_channel / ini
```

The host uses existing public `Controller(module=...)` and `serve(controller_factory=..., process_factory=...)`. It does not modify, subclass, or monkey-patch production GUI/backend/controller/service or bypass rules by replacing GUI snapshots. The service runs on a separate host thread; Controller calls remain serialized on the service worker.

The preview-process factory is also injected externally: it returns restricted G0/G1 geometry while the service retains asynchronous jobs/pagination and the GUI retains its original receiver. Preview explicitly states that it is not LinuxCNC interpreter output.

Each run creates a private `/tmp/cnc-api-*` directory (0700), socket (0600), test INI, tool table, parameter file, and QSettings, and copies a demo program. Exit removes temporary files. Production settings are untouched; other files chosen in dialogs are still handled by the original application under existing rules.

## Interactive steps

1. Click Show Main Window in the separate External Injection Test Console. Initial state is emergency stop, power off, unhomed.
2. In the original GUI, F1 releases emergency stop and F2 enables power. In Guided Device Control, click Home All. Simulated homing takes about one second, with reference X0 Y0 Z5.
3. Press R or Run. The demo traces a 40 × 30 mm rectangular tool centerline at Z=-1, then retracts to Z5 and stops the spindle. Cutter-radius compensation is disabled.
4. P pauses with stationary coordinates; S resumes; Esc stops. Professional mode supports T for single-step. Both layouts share one session and may switch while running/paused.
5. Choose 1×, 2×, 5×, or 10× in the console to accelerate test motion/homing. The 120 ms command acknowledgement delay remains wall-clock time.
6. Inject External Emergency Stop, Disconnect NML, or Inject Drive Alarm and observe original GUI state, disabled actions, and errors. Minimize the main window to reach an obscured console; Show Main Window restores it.

NML disconnect simulates unavailable status/command channels while the socket service remains online. A running program may continue; this is not emergency stop. Reconnection reads new state without replaying unfinished commands. External emergency stop stops motion and disables power; power must be enabled again after clearing it. Drive alarms use the original `error_channel` and stop test motion.

Optional arguments:

```sh
app/desktop/.venv/bin/python app/desktop/tests/interactive/main.py \
  --interface professional \
  --report app/desktop/artifacts/simulation/interface-interaction.json
```

`--program /absolute/path/example.ngc` loads a copy of another supported program; `--capture /tmp/interface.png` captures the main window after startup and exits. Reports retain original desktop snapshots, interface command serials, delayed acknowledgements, and fault-injection events, up to the latest 500 events.

## Supported scope

- Simulates `stat().poll()`, increasing `command()` serials/delayed acknowledgements, `error_channel().poll()`, and INI queries.
- Emergency stop, power, mode changes, home/unhome, continuous/incremental jog, jog stop, program open, run/pause/resume/stop/step.
- Feed/rapid overrides affect motion; maximum velocity limits program motion; spindle, coolant, brake, and switch feedback.
- Restricted programs must explicitly initialize G21/G17/G90/G94/G40/G49/G54/G80, use numeric G0/G1, XYZ, F, S, and M2/M3/M5/M9, and end with M2.
- MDI, touch-off, coordinate-system changes, tool changes/table reload, run-from-line, arcs, macros, and subroutines are unimplemented and fail explicitly. Optional stop/block delete provide switch state only; the parser rejects M1 and `/` blocks.

This substitutes external API behavior with linear position feedback for GUI tests. It does not simulate acceleration, servo errors, encoders, physical limit/home switches, HAL timing, collisions, or material removal, and is not real LinuxCNC interpreter or machine acceptance.

## File ownership and verification

| File | Responsibility |
| --- | --- |
| `tests/interactive/main.py` | External assembly of original window/backend and test host |
| `tests/interactive/service_host.py` | Private socket, original service, preview factory injection, temporary configuration lifecycle |
| `tests/interactive/vendor.py` | LinuxCNC Python API substitute, delayed acknowledgements, linear motion, fault input |
| `tests/interactive/linear_program.py` | Strictly restricted demo parser shared by preview/motion |
| `tests/interactive/backend.py`, `Controls.qml` | Separate console injecting faults through a thread-safe queue |
| `tests/test_simulation.py` | Deterministic original Controller tests and original DesktopBackend/service socket integration |
| `tests/programs/rectangle-demo.ngc` | Rectangular demo program |

Paths are relative to `app/desktop/`.

```sh
QT_QPA_PLATFORM=offscreen app/desktop/.venv/bin/python app/desktop/tests/test_simulation.py -v
```

Tests use public interfaces without reading production private fields. They cover delayed acknowledgements, homing, geometry/rejection of unsupported programs, pause/resume/stop/completion, single-step, external emergency stop, disconnect without replay, jog stop, overrides, errors, and preparation → run → pause → resume → completion → reconnect over real sockets. Existing regressions still use `ctest --test-dir build --output-on-failure`; this test runs independently without changing the production build entry point.
