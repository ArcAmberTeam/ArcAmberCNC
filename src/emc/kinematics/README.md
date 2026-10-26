# Machine kinematics

[Project module map](../../../docs/module-map.md)

## Role and language

Primarily C, with some C++; usually called by the motion module during real-time calculations.

Converts between tool/workspace axis coordinates and machine joint positions to represent a specific mechanical structure.

## Key code and communication

`kinematics.h` defines interfaces; `trivkins.c`, `xyzac-trt-kins.c`, `xyzbc-trt-kins.c`, and others implement different structures.

The motion module calls forward/inverse kinematics interfaces; machine configuration selects the implementation.

## Responsibility boundaries

Axis coordinates and joints are distinct concepts. This module does not parse program text, determine button layouts, or directly drive hardware. Do not assume one five-axis model fits every five-axis machine.

This is retained LinuxCNC core code, not part of the current Web static build artifact. Our Python service has not yet connected to these control paths. This document describes existing responsibilities without adding interfaces or changing upstream dependencies.

Changes here require appropriate native LinuxCNC builds and functional verification. A passing Web or Tauri build does not establish that this module runs. Real-time behavior additionally requires verification on the target Linux host.
