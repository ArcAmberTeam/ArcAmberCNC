# Trajectory planning

[Project module map](../../../docs/module-map.md)

## Role and language

C; participates in real-time motion execution.

Manages motion-segment queues, computes path velocity, acceleration/deceleration, and segment blending, and supplies planning results each cycle.

## Key code and communication

`tp.h` is the planning interface; `tp.c` is the main implementation. `tc.c` and `tcq.c` manage segments/queues, `blendmath.c` blending calculations, and `tpmod.c` module assembly.

Called by motion; accepts linear/arc segments and constraints, returning path position and execution status.

## Responsibility boundaries

Does not parse G-code text, receive webpage requests, or define machine-specific forward/inverse kinematics. UI refresh-rate changes should not change this module.

This is retained LinuxCNC core code, not part of the current Web static build artifact. Our Python service has not yet connected to these control paths. This document describes existing responsibilities without adding interfaces or changing upstream dependencies.

Changes here require appropriate native LinuxCNC builds and functional verification. A passing Web or Tauri build does not establish that this module runs. Real-time behavior additionally requires verification on the target Linux host.
