# Native LinuxCNC source navigation

[Project module map](../docs/module-map.md)

This directory contains the LinuxCNC control core and related tools. See root `VERSION` for the repository version. The new Vue UI is in `../frontend/` and the new local Python service in `../backend/`; neither replaces the motion implementation here.

| Module | Responsibility |
| --- | --- |
| [Task](emc/task/README.md) | Task and program execution coordination |
| [G-code interpreter](emc/rs274ngc/README.md) | Program semantics and canonical actions |
| [Trajectory planning](emc/tp/README.md) | Motion-segment queues, velocity, and blending |
| [Real-time motion](emc/motion/README.md) | Cyclic motion, homing, and motion feedback |
| [Kinematics](emc/kinematics/README.md) | Axis-coordinate/joint-position conversion |
| [Peripheral operations](emc/iotask/README.md) | I/O coordination and handshakes, including tool changes |
| [Message definitions](emc/nml_intf/README.md) | Internal LinuxCNC messages and canonical action interfaces |
| [Python interface](emc/usr_intf/python-interface/README.md) | Compiled Python access to LinuxCNC |
| [NML support libraries](libnml/README.md) | Communication and shared support code |
| [HAL](hal/README.md) | Signals, control components, and device drivers |
| [RTAPI](rtapi/README.md) | Real-time runtime adaptation |

This navigates the main control chain, not every upstream tool/driver directory. `emc/usr_intf/` retains QtVCP, Gmoccapy, and other tools. Native AXIS and its dedicated entry points were removed; not all native UIs were deleted.
