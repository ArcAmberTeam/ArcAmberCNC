# Task execution coordination

[Project module map](../../../docs/module-map.md)

## Role and language

C++; non-real-time user space.

Receives UI commands, coordinates manual, automatic, and MDI modes, invokes the G-code interpreter, and schedules execution according to motion and I/O preconditions and postconditions.

## Key code and communication

`emctaskmain.cc` is the main loop; `emccanon.cc` connects interpreter canonical actions to execution commands; `taskintf.cc` and others expose subsystem interfaces.

Communicates upstream through NML command, status, and error channels. Downstream, it calls the motion interface and coordinates I/O; that interface exchanges data with the real-time module through shared memory.

## Responsibility boundaries

Task modes and execution constraints remain LinuxCNC responsibilities; Python application prechecks cannot replace them. This module does not draw the UI or directly produce each cycle of motor output.

This is retained LinuxCNC core code, not part of the current Web static build artifact. Our Python service has not yet connected to these control paths. This document describes existing responsibilities without adding interfaces or changing upstream dependencies.

Changes here require appropriate native LinuxCNC builds and functional verification. A passing Web or Tauri build does not establish that this module runs. Real-time behavior additionally requires verification on the target Linux host.
