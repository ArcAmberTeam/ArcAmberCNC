# Real-time motion execution

[Project module map](../../../docs/module-map.md)

## Role and language

Primarily C; `usrmotintf.cc` is the C++ user-space access interface.

Processes motion commands, performs periodic motion calculations, jogging, homing, and motion-state checks, and connects trajectory planning, kinematics, and HAL.

## Key code and communication

`motion.c` handles initialization, `command.c` commands, `control.c` cyclic control, `homing.c` homing, and `usrmotintf.cc` user-space/motion shared memory.

Task reads/writes shared memory through the user-space motion interface. The real-time side uses `tp`, `kinematics`, and HAL, exposing commanded positions/execution state and reading feedback.

## Responsibility boundaries

This is independent of non-real-time UI refresh loops; it must not depend on timely Python, JSON, network round trips, or webpage responses. Shared memory is not an application interface for Vue or Python to write directly.

This is retained LinuxCNC core code, not part of the current Web static build artifact. Our Python service has not yet connected to these control paths. This document describes existing responsibilities without adding interfaces or changing upstream dependencies.

Changes here require appropriate native LinuxCNC builds and functional verification. A passing Web or Tauri build does not establish that this module runs. Real-time behavior additionally requires verification on the target Linux host.
