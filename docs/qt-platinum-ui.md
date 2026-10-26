# Qt platinum UI and component structure

On 2026-10-24, the native QML machining workspace was adjusted to the user's CNC Platinum Visual Style Manual and AI Refactoring Specification. It uses warm white, champagne gold, red stop semantics, and white panels while preserving LinuxCNC protocol, action IDs, operation permissions, and jogging lifecycle.

## File responsibilities

| File | Responsibility |
| --- | --- |
| `qml/BetterCnc/Ui/Theme.qml` | Central colors, fonts, control sizes/spacing; `accentFill` is gold fill, `accent` readable dark gold text/focus |
| `qml/BetterCnc/Ui/Ui*.qml` | Shared button/input/check/list/slider/icon appearance and focus |
| `qml/Main.qml` | Default 1440×900 window, close/focus lifecycle |
| `qml/Workspace.qml` | Wide/narrow layouts, panel composition, backend feedback, jog-key ownership |
| `qml/WorkspaceShortcuts.qml` | Noncontinuous-jog shortcuts with explicitly injected state/actions |
| `qml/WorkspaceStatus.qml` | Always-visible bottom connection/operation status and preview limitations |
| `qml/BetterCnc/Chrome/MachineStatus.qml` | Maps actual snapshots to text/colors without deciding permissions |
| `qml/BetterCnc/Chrome/ChromeBar.qml` | Menus/toolbar, with Stop outside scrolling |
| `qml/BetterCnc/Manual/ManualPanel.qml` | Manual groups, jog gestures, release/focus-loss stop, internal controls |
| `qml/BetterCnc/Manual/MdiControls.qml` | Internal MDI history/input/submission |
| `qml/BetterCnc/Manual/OverrideControls.qml` | Internal override/velocity controls reporting user edits |
| `qml/BetterCnc/Program/ProgramPanel.qml` | Program document, 40 px rows, selection/execution lines |
| `qml/BetterCnc/Toolpath/ToolpathPanel.qml`, `ToolpathCanvas.qml` | Existing coordinates/segments, gold cutting paths, blue dashed rapids, narrow-window adaptation |

The two new Manual controls are internal in `qmldir`; other modules still use `ManualPanel`. `MachineStatus` is a public Chrome presentation type. CMake recursively collects/installs production QML; fixtures stay in `tests/` and are not installed.

## Layout and behavior

- Guided/professional interfaces share the platinum theme; see [dual-interface notes](qt-dual-interface.md) for layout and interaction.
- Professional places Manual left, Toolpath/Coordinates upper right, and Program lower right. Guided uses Prepare/Preview/Device pages. Minimum window remains 760×640; the device panel is 304 px, or 280 px compact, with independent scrolling.
- All original menus/actions remain accessible. Toolbar scrolls horizontally while labeled Stop stays fixed; emergency stop and ordinary stop retain distinct semantics.
- Shortcuts isolate editable input, dialogs, and menus. Continuous-jog press/release remains in Workspace/ManualPanel rather than the shortcut presentation component.
- Snapshot-derived status prioritizes disconnect over stale state, never treats idle as completed machining, and generates no machining percentage.

## Verification and local preview

```sh
cmake --build build --parallel
ctest --test-dir build --output-on-failure
app/desktop/.venv/bin/python app/desktop/tests/visual_preview.py
```

The final command opens the real UI explicitly labeled Visual Acceptance · Test Data with QML FakeBackend. Buttons record requests without service/machine access. Use `--scenario offline` or `--scenario error` for disconnection/errors.

Headless screenshot:

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
app/desktop/.venv/bin/python app/desktop/tests/visual_preview.py \
  --width 1024 --height 768 --scenario offline --capture /tmp/cnc-offline.png
```

Initial platinum screenshots are in local Git-ignored `app/desktop/artifacts/platinum/`; current dual-interface screenshots are in `app/desktop/artifacts/dual-ui/`. Geometry is fixed test segments, not actual G-code interpreter output.

New layout tests verify nonoverlapping panels, preview width, stop access, and status bars at four sizes. New status tests cover disconnected, emergency stop, running, paused, and unknown outcomes. Existing menu/input/jog/file-edit/program-selection/Python-interface tests remain. Line-selection tests use control targeting instead of old-theme fixed pixels.

## Differences from reference images

The application is a program-text/toolpath-segment console without a project tree, materials library, process-edit routes, or material-removal engine. The left area therefore uses real program listings and the center is explicitly Toolpath Preview; do not add fictitious machine models, process parameters, solids, or playback progress from references.

Overlays use the permitted solid `#FAF9F6` fallback without background blur or new rendering dependencies. Status/coordinates update immediately without unnecessary animation. Existing Canvas drawing remains. macOS software-rendered/scaled screenshots do not replace Debian 13 / Intel target acceptance or establish machine-operation acceptance.
