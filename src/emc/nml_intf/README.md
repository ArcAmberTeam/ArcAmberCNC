# LinuxCNC messages and canonical action definitions

[Project module map](../../../docs/module-map.md)

## Role and language

C/C++.

Defines LinuxCNC commands, status, message formats, canonical actions, and shared structures used by Task, UI interfaces, I/O, and other modules.

## Key code and communication

`emc.hh` and `emc_nml.hh` define messages; `emc.cc` provides message-format handling; `canon.hh` defines interpreter canonical actions; `interpl.hh` owns the interpreter command-list interface.

Depends on lower-level NML/RCS libraries and is used by LinuxCNC control processes.

## Responsibility boundaries

These are LinuxCNC internal contracts, not our Rust↔Python JSON protocol. Adding a webpage field normally does not require changing these internal messages.

This is retained LinuxCNC core code, not part of the current Web static build artifact. Our Python service has not yet connected to these control paths. This document describes existing responsibilities without adding interfaces or changing upstream dependencies.

Changes here require appropriate native LinuxCNC builds and functional verification. A passing Web or Tauri build does not establish that this module runs. Real-time behavior additionally requires verification on the target Linux host.
