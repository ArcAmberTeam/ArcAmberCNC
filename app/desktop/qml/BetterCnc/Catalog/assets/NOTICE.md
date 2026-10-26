# Qt static asset sources

This directory contains Qt assets and provenance inherited from the former Web UI. The historical resource snapshot corresponds to repository revision `607f246518b0f41bb7240ba8777751ce25889ff7` (based on LinuxCNC 2.9.10). Native AXIS toolbar redraws/generators were withdrawn; Web was removed. Qt retains licenses/attribution for assets it uses; builds neither read deleted directories nor load remote CDNs.

## Redrawn toolbar

These files belonged to the historical Lucide redraw:

```text
tool_estop.gif      tool_power.gif       tool_open.gif
tool_reload.gif     tool_run.gif         tool_step.gif
tool_pause.gif      tool_stop.gif        tool_blockdelete.gif
tool_optpause.gif   tool_zoomin.gif      tool_zoomout.gif
tool_axis_z.gif     tool_axis_z2.gif     tool_axis_x.gif
tool_axis_y.gif     tool_axis_y2.gif     tool_axis_p.gif
tool_rotate.gif     tool_clear.gif       resume_inhibit.gif
```

Upstream: [Lucide](https://github.com/lucide-icons/lucide), source revision `951813ce76a859d4d8b145366972cbb237147a4e`. Original icon mappings, dimensions, SVGs, and redraw notes are in historical [manifest.json](https://github.com/Xamber-Software/BetterLinuxCNC/blob/607f246518b0f41bb7240ba8777751ce25889ff7/share/axis/images/toolbar-source/manifest.json) and [README.md](https://github.com/Xamber-Software/BetterLinuxCNC/blob/607f246518b0f41bb7240ba8777751ce25889ff7/share/axis/images/toolbar-source/README.md). Changes include colors, some solid shapes, and AXIS-specific marks; Qt does not redraw these historical GIFs again.

Copyright and licenses:

- Copyright (c) 2026 Lucide Icons and Contributors — ISC.
- Some icons derive from Feather: Copyright (c) 2013-present Cole Bemis — MIT.

Full notices are preserved unchanged in [TOOLBAR-LICENSE](TOOLBAR-LICENSE), from the [historical LICENSE](https://github.com/Xamber-Software/BetterLinuxCNC/blob/607f246518b0f41bb7240ba8777751ce25889ff7/share/axis/images/toolbar-source/LICENSE). ISC and MIT apply; withdrawal of native assets does not change licenses for existing copies. GIF transparent edges were processed for AXIS `#d9d9d9` controls. Their provenance remains historical documentation; this directory does not contain those GIFs. The current dark toolbar uses original vector paths in `BetterCnc.Ui`.

## Other AXIS images

```text
axis-16x16.png  axis-24x24.png  axis-32x32.png  axis-48x48.png
banner.gif     close.gif       spindle_ccw.gif spindle_cw.gif
std_error.gif  std_info.gif    std_warning.gif tool_verify.gif
```

These originated at the same `share/axis/images/` path. Under `Files: *` in repository [debian/copyright](../../../../../../debian/copyright), they are `GPL-2+`, GPL version 2 or later, copyright The LinuxCNC Developers and listed contributors. Full license: [COPYING](../../../../../../COPYING). This directory currently retains `axis-48x48.png`; the historical list does not mean Qt includes/uses the other images.

## Program examples and UI references

The former Web sample copied [share/axis/images/axis.ngc](https://github.com/Xamber-Software/BetterLinuxCNC/blob/e470d7aa6268a4ff56963cb8e162f2004ba89736/share/axis/images/axis.ngc). Chinese localization translated explanatory comments only, preserving instructions, parameters, and line count; it follows the repository's general GPL-2+ entry. `BetterCnc.Catalog` sampleProgram inherits this historical example, never production state. Comments identify it as AXIS splash G-code, not an actual milling job.

UI structure references historical share/axis/tcl/axis.tcl and src/emc/usr_intf/axis/scripts/axis.py, whose upstream copyright notices name Jeff Epler and Chris Radek under GPL-2.0-or-later. Qt UI retains repository GPL-2.0-or-later licensing.

The former Web toolpath SVG was illustrative. Current Qt draws service-interpreted segments and actual traces. This document records existing provenance without changing original licenses; distribute applicable licenses/copyright notices with Qt.
