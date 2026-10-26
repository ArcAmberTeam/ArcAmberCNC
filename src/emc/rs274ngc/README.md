# G-code interpreter

[Project module map](../../../docs/module-map.md)

## Role and language

Primarily C++, with Python extension integration; normally runs in a non-real-time context.

Interprets G/M codes, modal state, coordinate transforms, tool compensation, and canned cycles, producing canonical actions.

## Key code and communication

`rs274ngc_interp.hh` and `interp_base.hh` are interpreter interfaces. `interp_read.cc` reads/parses; `interp_convert.cc`, `interp_arc.cc`, and others implement specific conversions.

Called by Task or dedicated interpretation tools. It passes actions to execution through canonical interfaces in `../nml_intf/canon.hh`. Preview tools can use a different action receiver.

## Responsibility boundaries

It does not draw the GUI, drive hardware, or replace real-time trajectory planning. Our current SVG preview is not connected to this interpreter; future preview interpretation should be handled separately.

This is retained LinuxCNC core code, not part of the current Web static build artifact. Our Python service has not yet connected to these control paths. This document describes existing responsibilities without adding interfaces or changing upstream dependencies.

Changes here require appropriate native LinuxCNC builds and functional verification. A passing Web or Tauri build does not establish that this module runs. Real-time behavior additionally requires verification on the target Linux host.
