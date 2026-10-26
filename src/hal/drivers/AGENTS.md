# HAL device driver boundaries

Follow root `AGENT.md` and parent `src/hal/AGENTS.md`.

This directory owns HAL device drivers and their generators, firmware resources, and documentation. Keep source/resources together by complete device capability, not implementation language or extension. User-space devices such as Modbus, VFDs, Shuttle, and XHC handwheels live in sibling `user_comps/`.

Drivers connect to the control core through existing public HAL/RTAPI interfaces. Registers, USB, serial, buses, and firmware details remain private. Do not duplicate platform-common logic across CPU directories. Retain existing boundaries for Mesa, Raspberry Pi, BeagleBone, and generic GPIO. CPU architecture, device platform, and real-time runtime are distinct layers.

The sole physical source is `src/hal/drivers/`, built from `src/`. Do not run standalone builds here or create a second source copy. Preserve generated files and installed interfaces; do not export private headers to the application layer.

Verification: `.github/ci/test_native_layout.py` and `.github/ci/native-check.sh drivers` on Debian 13. Build success does not establish device or real-time behavior. README content is maintained by humans.
