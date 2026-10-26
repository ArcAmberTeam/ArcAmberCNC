# Real-time runtime adaptation

[Project module map](../../docs/module-map.md)

## Role and language

Primarily C, with some C++ support files.

Provides tasks, timing, shared memory, and other low-level facilities to real-time modules, adapting to the specific real-time runtime.

## Key code and communication

`rtapi.h`, `rtapi_app.h`, and related headers define interfaces. `uspace_rtapi*`, `rtai_rtapi.c`, and others implement backends selected by build/runtime configuration.

Used by HAL and real-time modules. Target deployment uses Debian 13 PREEMPT_RT, but actual target verification is still required.

## Responsibility boundaries

RTAPI does not interpret G-code, compute machine geometry, or carry webpage communication. The historical extensionless `README` contains old platform/build instructions and must not be treated directly as current Debian deployment steps.

This is retained LinuxCNC core code, not part of the current Web static build artifact. Our Python service has not yet connected to these control paths. This document describes existing responsibilities without adding interfaces or changing upstream dependencies.

Changes here require appropriate native LinuxCNC builds and functional verification. A passing Web or Tauri build does not establish that this module runs. Real-time behavior additionally requires verification on the target Linux host.
