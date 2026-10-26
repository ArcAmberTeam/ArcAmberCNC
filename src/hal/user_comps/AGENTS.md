# HAL user-space component and device driver boundaries

Follow root `AGENT.md` and parent `src/hal/AGENTS.md`.

This directory owns complete user-space HAL capabilities, including Modbus, VFD, Shuttle, XHC-HB04, and XHC-WHB04B-6 drivers/resources. C, C++, and Python implementations remain with their devices/components; do not create top-level language modules.

Drivers connect to the control core through existing public HAL/RTAPI interfaces. USB messages, serial, device state, bus details, and HAL adaptation are internal implementation. Preserve existing HAL pins, parameters, and CLIs; application code must not directly import implementation headers.

The sole physical source is `src/hal/user_comps/`, built by the upstream Make entry point in `src/`. Do not add duplicate source or cross-root compatibility links. C++ HAL bindings and mixed-language HAL tools stay with their HAL capabilities rather than moving here by extension.

Verification: `.github/ci/test_native_layout.py` and `.github/ci/native-check.sh drivers` on Debian 13. User-space component changes also require affected targets from the same native Make entry point. XHC handwheel targets are `../bin/xhc-hb04` and `../bin/xhc-whb04b-6`. Builds do not access devices or load machine-control modules and do not establish actual device behavior. README content is maintained by humans.
