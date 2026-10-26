# Peripheral operation coordination

[Project module map](../../../docs/module-map.md)

## Role and language

C++; non-real-time user space.

Handles tool-change, coolant, and related auxiliary I/O requests and handshakes, reporting completion/errors to the execution coordinator.

## Key code and communication

`ioControl.cc` and `ioControl_v2.cc` are the existing I/O control implementations; configuration and startup determine which is used.

Receives relevant task commands through NML, connects external logic through HAL pins, and reports operation status.

## Responsibility boundaries

This is not the sole entry point for all real-time I/O; motion-synchronized I/O and hardware access have their own motion/HAL paths. Never replace actual electrical handshakes with local state inferred from UI clicks.

This is retained LinuxCNC core code, not part of the current Web static build artifact. Our Python service has not yet connected to these control paths. This document describes existing responsibilities without adding interfaces or changing upstream dependencies.

Changes here require appropriate native LinuxCNC builds and functional verification. A passing Web or Tauri build does not establish that this module runs. Real-time behavior additionally requires verification on the target Linux host.
