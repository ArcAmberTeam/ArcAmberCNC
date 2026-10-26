# Native AXIS removal boundaries

This removal concerns the native **AXIS GUI**. Web was subsequently removed on 2026-10-08; the official UI belongs to `app/desktop/`. LinuxCNC interpreter, trajectory planning, real-time motion, HAL, drivers, and kinematics remain. In motion control, `axis` means a coordinate axis, not the removed UI.

## Removed

- AXIS main program, axis-remote, UI-specific helpers, and old build entry points in `src/emc/usr_intf/axis/`.
- Main-window Tcl, toolbar, splash, UI configuration, and dedicated resources in `share/axis/`.
- `bin/profile_axis`, AXIS-specific propertywindow, and axis/axis-remote command manuals.
- AXIS installation entries in Makefile, Debian file lists, and translation/manual lists; shutdown no longer invokes axis-remote.

## Shared capability ownership

| Module | Retained capability and public entry | Consumers |
| --- | --- | --- |
| `src/emc/usr_intf/python-interface/` | Builds `lib/python/linuxcnc.so`; preserves full existing `import linuxcnc` API | Python control clients, diagnostics, future control gateways |
| `src/emc/usr_intf/python-tools/` | Existing standalone mdi, linuxcnctop, hal_manualtoolchange, image-to-gcode, debuglevel, etc. | HAL configurations and upstream tools |
| `src/emc/usr_intf/tk-support/` | Builds `_togl.so`; accessed through existing `rs274.OpenGLTk` | Vismach and existing previews |
| `share/linuxcnc/tk-support/` | Shared Tcl dialogs and three message images, accessed through Python `nf` | Tool-change prompts and program generators |

Shared Python control bindings moved unchanged, preserving command, status, error-channel, and positionlogger APIs. Existing bindings still contain OpenGL positionlogger and retain linking dependencies; this does not claim a graphics-library-free LinuxCNC build.

QtVCP, Gmoccapy, Touchy, configuration wizards, and standalone diagnostics are other upstream programs, not AXIS's main UI, and were not removed. They are not included in Qt build artifacts. Shared Tk dependencies support these tools, not a hidden AXIS copy.

## Legacy configuration and history

Upstream INI/HAL configurations and manuals remain for control-engine development and UI reference. Configurations specifying `DISPLAY = axis`, including paths to axis/axis.py, exit before starting HAL, real-time components, or Task and explain that AXIS was removed. Old configurations are not automatically converted to Qt or another UI. Existing `send_to_axis` callbacks retain failure returns so pyngcgui prompts file saving rather than starting remote commands.

Running the control engine requires an available control entry and corresponding configuration migration. Qt requires explicit independent controller service and machine-session configuration; see [Qt migration notes](qt-qml-migration.md).

Qt assets belong to `app/desktop/qml/BetterCnc/Catalog/`. Historical Web design material remains in Git, with source links pinned before removal. AXIS mentions in history/translations do not mean it can still be built or installed.

## Verification

Module CI source-checks cover AXIS removal boundaries, Makefile targets, and launcher rejection of legacy configurations. Qt, Python, Rust, and native modules have their own CI checks. Lightweight checks do not replace full native Linux builds, installation, and runtime acceptance.
