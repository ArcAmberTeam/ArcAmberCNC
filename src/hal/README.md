# Hardware abstraction layer

[Project module map](../../docs/module-map.md)

## Role and language

Primarily C, with C++, Python, and component definition files.

Connects software functions and device signals as pins, signals, parameters, and execution functions, supporting collaboration among motion, control components, and hardware drivers.

## Key code and communication

`hal.h` and `hal_lib.c` provide the core interface/implementation. `components/` owns control components, `drivers/` hardware drivers, `user_comps/` user-space components, and `utils/` configuration tools.

Connects motion and other control logic above to drivers/devices below. HAL supports both real-time and non-real-time components; execution context depends on component/thread configuration.

## Responsibility boundaries

HAL is not a control card or a guarantee that the whole system is real time. UI redesign should not change HAL wiring, and ordinary buttons must not bypass the controller service to write arbitrary pins.

This is retained LinuxCNC core code, not part of the current Web static build artifact. Our Python service has not yet connected to these control paths. This document describes existing responsibilities without adding interfaces or changing upstream dependencies.

Changes here require appropriate native LinuxCNC builds and functional verification. A passing Web or Tauri build does not establish that this module runs. Real-time behavior additionally requires verification on the target Linux host.
