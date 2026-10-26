# GUI regression tests without LinuxCNC

GUI tests use Qt Quick Test to load the real QML window and inject `app/desktop/tests/FakeBackend.qml`. It provides deterministic snapshots, program text, and request records without sockets, LinuxCNC, simulators, or machine operations. The production launcher never loads it.

## Interactive manual tests

Run from the repository root:

```sh
app/desktop/.venv/bin/python app/desktop/tests/interactive/main.py
```

This opens the real GUI labeled Interactive Test and a separate console. Only PySide6 is required; the C++ test launcher need not be built first. Closing either window exits the test.

1. Click Run, Spindle, Coolant, or press/release jogging in the real UI. The console lists request IDs/arguments and the jog-stop call count.
2. Select Disconnected, Power Off, Emergency Stop, Running, Paused, or Ready in the console and observe disabled actions/state. Requests do not update snapshots automatically; the console injects feedback independently.
3. Drag X/Y/Z sliders to inspect coordinates/actual traces, change the execution line to inspect program scrolling/highlights, and select program lines to inspect corresponding segments.
4. Use Operation Error or Preview Failure to inspect errors. Load Example restores the rectangular sample; Reset Test restores initial state.

Coordinates, programs, and toolpaths are explicit test data; the rectangle has not passed through a G-code interpreter. Open/save only record requests, without disk I/O. MDI does not execute and jogging does not automatically change coordinates. The console keeps up to 100 recent requests and supports clearing. Production entry points/install artifacts exclude this test entry.

## Local execution

Requires Qt 6.8+ Quick, QuickControls2, and QuickTest development components, CMake, and a C++17 compiler. Python backend/startup checks also need Python 3.11+ and PySide6.

From the repository root, adjust Qt/Python paths for the installation:

```sh
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$HOME/Qt/6.12.0/macos" \
  -DPython3_EXECUTABLE="$PWD/app/desktop/.venv/bin/python"
cmake --build build --parallel
ctest --test-dir build -R '^qml-ui$' --output-on-failure
```

CTest sets `QT_QPA_PLATFORM=offscreen`, `QT_QUICK_BACKEND=software`, and Basic controls automatically; no manually opened GUI or controller service is required.

Also check module boundaries, production QML, Python public interfaces, and offline startup:

```sh
ctest --test-dir build \
  -R '^(qml-ui|module-boundaries|qml-lint|python-integration|desktop-startup)$' \
  --output-on-failure
```

Python public-interface tests use temporary Unix sockets and controlled service substitutes; the runtime must permit local sockets. If macOS sandboxing restricts graphics/sockets, run in an ordinary local terminal.

## Coverage

- `tst_workspace.qml`: jog press/release, focus/mode changes, offline disablement, MDI, overrides, touch-off, and layout.
- `tst_chrome.qml`: menus, toolbar, shortcuts, dialogs, edit drafts, asynchronous failures.
- `tst_panels.qml`: program-line selection, coordinate conversion, preview layers, small windows.

Thirteen added workspace scenarios cover:

- No mouse/keyboard jog requests when disconnected, powered off, in emergency stop, busy, in automatic mode, without an available axis, or capability-disabled (seven scenarios).
- Disconnect while jogging; reconnect/release does not replay old commands, and only a new keypress submits a new request.
- Offline zoom, views, and preview/readout tabs remain usable without control commands.
- Empty, whitespace, nonnumeric, or overflowing touch-off input keeps the dialog open with an error; only corrected valid input submits (four scenarios).

These verify UI behavior/command intent, not actual LinuxCNC execution, motion, or hardware safety. Preview test data is not real G-code interpretation.
