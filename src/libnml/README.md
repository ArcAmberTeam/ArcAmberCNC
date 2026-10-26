# Interprocess communication and shared support libraries

[Project module map](../../docs/module-map.md)

## Role and language

C/C++, primarily C++ communication classes.

Provides NML, CMS, RCS, and other messaging/channel infrastructure. The directory also contains upstream shared support code for INI parsing, pose mathematics, and related functions.

## Key code and communication

`nml/`, `cms/`, and `rcs/` own communication foundations; `inifile/` configuration reading; `posemath/` pose mathematics.

Used by LinuxCNC message definitions and control processes. Local NML configuration may use shared-memory channels; distinguish these from the dedicated Task↔Motion shared-memory interface.

## Responsibility boundaries

Does not own machine operating rules and is not a frontend network service. Our Unix socket serves Rust↔Python communication and does not replace LinuxCNC internal NML.

This is retained LinuxCNC core code, not part of the current Web static build artifact. Our Python service has not yet connected to these control paths. This document describes existing responsibilities without adding interfaces or changing upstream dependencies.

Changes here require appropriate native LinuxCNC builds and functional verification. A passing Web or Tauri build does not establish that this module runs. Real-time behavior additionally requires verification on the target Linux host.
