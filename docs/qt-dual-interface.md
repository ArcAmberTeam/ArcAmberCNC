# Guided and professional Qt interfaces

Both interfaces share the platinum theme, one backend connection, program document, and feature panels. Professional mode is the default. Top-level Settings opens fullscreen settings; switch Guided/Professional under Interface Layout. Mode and step are presentation state for the current window and are not persisted across application restarts.

## References and choices

- [Official QtDragon documentation and screenshots](https://www.linuxcnc.org/docs/html/gui/qtdragon.html): reference for grouped manual controls, coordinates, toolpaths, and programs. Professional mode keeps manual/MDI and overrides on the left, with toolpath/coordinates above the program on the right and a draggable height divider.
- [Official Bambu Studio project](https://github.com/bambulab/BambuStudio) and [window source](https://github.com/bambulab/BambuStudio/blob/master/src/slic3r/GUI/MainFrame.cpp): reference for Prepare / Preview / Device task pages. Guided mode adapts these to Prepare Program / Check Toolpath / Device Control, with text toolbars, status cards, and next-step actions.

This adapts CNC workflow without copying either project's source, icons, or trademarks or integrating Bambu cloud, slicing, cameras, or material removal. Preparation reads existing G-code; 3D-printer temperature, filament, and slicing parameters are not CNC parameters. Guided mode does not relax server restrictions or infer machining safety from cards.

## Layout and reuse

| File | Ownership |
| --- | --- |
| `qml/Workspace.qml` | Composes the sole ManualPanel, ToolpathPanel, and ProgramPanel; owns presentation/jogging lifecycle; delegates actions to the existing backend |
| `qml/WorkspaceLayout.qml` | Public contract for layout inputs and panel rectangles/visibility, without machine state |
| `qml/ProfessionalLayout.qml` | Manual left, toolpath/coordinates upper right, program lower right |
| `qml/GuidedLayout.qml` | Geometry/visibility for prepare, preview, and device steps |
| `qml/WorkspaceGuide.qml` | Guided cards observing existing state and public ChromeActions; fixed bottom actions and scrollable explanations |
| `qml/BetterCnc/Chrome/ChromeBar.qml` | Shared menus, mode switching, step navigation; full professional toolbar, guided text toolbar, fixed stop |
| `qml/WorkspaceShortcuts.qml` | Shared shortcuts; F3/F5 selects Device in guided mode; hidden manual controls ignore jog/home shortcuts |

At widths of at least 1280 px, guided preparation shows program, preview, and guidance together; narrower windows show program/guidance and move preview to the next step. Preview shows a large toolpath area plus guidance. Device shows toolpath/coordinates and complete manual controls, avoiding copied/simplified machine rules. Default window is 1024×600; minimum width remains 760 px.

Panels are not destroyed/recreated through Loader, so switching preserves unsubmitted MDI, selected program line, view, units, override feedback, selected axis, and jog increment. Switching submits no machining command; mode/step changes cancel the current jog gesture and call existing jog stop. Execution state still comes from the backend; page changes never imply completion.

## Operation and local interactive acceptance

Choose Guided or Professional under Settings → Interface Layout, then Return to Workspace. Existing F1 emergency stop, Esc stop, F3 manual, F5 MDI, and menus remain. Guided Pause becomes Resume after backend paused feedback and submits existing `program.resume`. Both layouts share `ChromeActions.canActivate` and service capabilities.

Interactive windows without LinuxCNC:

```sh
app/desktop/.venv/bin/python app/desktop/tests/visual_preview.py --interface guided
app/desktop/.venv/bin/python app/desktop/tests/visual_preview.py --interface professional
```

Also available: `--stage preview`, `--stage device`, `--scenario offline`, and `--scenario error`. FakeBackend is explicitly labeled Test Data; buttons record requests without hardware control or automatic simulation of real machine state. Switch modes within the same window.

Screenshot command:

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
app/desktop/.venv/bin/python app/desktop/tests/visual_preview.py \
  --interface guided --stage preview --width 760 --height 640 --capture /tmp/guided.png
```

Local screenshots are in Git-ignored `app/desktop/artifacts/dual-ui/`. Fixed test segments are not actual G-code interpreter output.

## Verification

Use CMake/CTest for QML UI, qmllint, module boundaries, Python/backend integration, and startup. Added interactive regressions cover:

- Switching retains MDI text, selected program line, toolpath view, and increment without extra commands.
- Guided navigation, rejection of arrow-key jogging with hidden manual controls, stopping jog on leaving Device, and F5 targeting MDI.
- Shared run permissions; disabled when offline/busy/rejected by backend; pause/resume/stop use original commands.
- Nonoverlapping panels at 760, 1024, 1280, and 1440 px for all three guided steps, visible stop/navigation, and primary guidance actions unobscured by scrolling.
- Professional divider and controls retained at the same widths.

macOS headless/local-window checks do not replace Debian 13 / Intel graphics or real-machine acceptance.

## Toolpath views and touch interaction

Both layouts share zoom, pan, and rotation in `ToolpathState`; switching does not reset the view. `ViewportGestures` emits camera signals only, `ViewportControls` provides touch buttons, and `ToolpathCanvas` projects/draws. These are internal Toolpath types and submit no machine commands. Rotation pivots around program center while preserving the projection base scale to prevent size jumps from repeated fitting. Coordinate updates redraw only lightweight overlays.

| Input | Behavior |
| --- | --- |
| Left mouse / one-finger drag | Pan by default; rotate around program center in Rotate mode |
| Middle / right mouse drag | Fixed pan / rotate |
| Mouse wheel | Pointer-anchored zoom, 10%–2000% |
| Two-finger touch | Pinch zoom plus pan; never interpreted as one-finger rotation |
| Trackpad | Qt native pinch zoom; pixel scrolling pans; Ctrl + pixel scrolling zooms |
| Double click / double tap | Clear pan, rotation, zoom and fit the current projection |
| Focused view arrows / PageUp, PageDown / Home | Pan / zoom / reset; no jog, home, or touch-off |

Preview header offers pan, rotate, zoom out/in, reset, and top view with 44-logical-pixel touch height. Narrow windows scroll this toolbar horizontally. Projection presets clear free rotation/pan/zoom; Top returns to XY. View/toolbar focus suspends manual jogging, axis-selection, homing, and touch-off shortcuts; global F1/Esc remain.

Jog buttons are 48×44 with touch guidance. Mouse press requests jogging immediately; touch/pen requires 250 ms hold, so taps/scroll gestures do not start. Movement beyond the system drag threshold, release, focus loss, inactive window, or disabled controls cancels. Moving back onto a canceled button does not restart. Focus loss during the hold delay cancels the pending start. Existing capability checks, service leases, and stop entry points remain.

Use the original UI, desktop backend, and controller service with only an externally injected LinuxCNC interface substitute:

```sh
app/desktop/.venv/bin/python app/desktop/tests/interactive/main.py
```

QML tests inject mouse, keyboard, and `touchEvent()` for pan, rotation, anchored zoom, two-finger transitions, double-tap reset, focus isolation, and jog cancellation. Qt Quick Test mouse release artificially advances event timestamps by 500 ms, so double-tap tests use touch events to avoid treating test-framework intervals as product behavior. See [Qt TapHandler](https://doc.qt.io/qt-6/qml-qtquick-taphandler.html) and [Qt Quick Test events](https://github.com/qt/qtdeclarative/blob/dev/src/qmltest/quicktestevent.cpp). macOS injected tests do not establish physical touchscreen, Debian driver, or real-machine acceptance.

## 1024×600 and fullscreen settings

Settings fills the application client area over the workspace, with fixed Back, Emergency Stop, and Stop at the top. It does not open another system window or toggle OS fullscreen. Sections are Interface Layout, Toolpath and Coordinates, and Machining Options, with touch scrolling and top navigation.

- Layout selection moved from the workspace into settings. Professional mode removes the old mode/brand rows. At widths of at least 1024 px, menus, settings, and machining actions share one 52 px row; Guided adds 44 px step navigation, totaling 96 px. Below 1000 px, menus/settings get a separate row to avoid squeezing actions. Window titles show only the program filename, or No Program Open.
- The main toolbar removes duplicate view/zoom/trace actions and optional-stop/block-delete switches. Toolpath pan/rotate/zoom/reset/top actions remain. Other projections, units, coordinate sources, grids, and visibility options are centralized in settings; existing menus remain compatible.
- Maximum velocity moves from Manual to Machining Options, observing the same read-only state and issuing `velocity.max`. Feed, rapid, spindle overrides, and jog speed remain in Manual. Optional-stop/block-delete switches await controller feedback rather than optimistic updates.
- At initial startup in a 600 px high window, program height defaults to 120 px to enlarge toolpath space; the divider remains adjustable. Settings does not destroy workspace panels; returning preserves view, selected line, MDI text, and jog increment.
- Entering settings first stops this session's jogging. Settings disables jog/run/home/F2/F3/F5 and other workspace shortcuts; F1 emergency stop, Esc stop, and header actions remain. Display preferences remain session-only, without INI writes or persistence across starts.

`WorkspaceSettings.qml` composes the page. Public `ToolpathSettings` and `ManualSettings` reuse their modules' existing presentation state and command entry points. No new control backend is added.

External-injection interactive tests also default to 1024×600, overridable with `--width`/`--height`. Acceptance covers both layouts, settings size, scroll/focus, offline display preferences, feedback-driven switches, jogging stop, and shortcut isolation. Physical touchscreens and target Linux graphics still require measurement.
