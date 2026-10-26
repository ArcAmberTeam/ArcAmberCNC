# Onsite axis mapping and v4 fix, 2026-10-26

The user confirmed original motor outputs and positive motion through onsite jogging:

| Original joint / stepgen | Physical axis | Original positive motion | v4 logical axis and adjustment |
| --- | --- | --- | --- |
| 0 / 00 | Y (left/right, 275 mm) | Right | joint 1 / Y uses stepgen.00; retain polarity |
| 1 / 01 | X (forward/back, 420 mm) | Forward | joint 0 / X uses stepgen.01; retain polarity |
| 2 / 02 | Z (up/down, 90 mm) | Down | joint 2 / Z uses stepgen.02; STEP_SCALE 200 → -200 |

After correction, X+ is forward, Y+ right, and Z+ up. The user specified homing X backward, Y left, and Z down. All axes use HOME_SEARCH_VEL=-2 mm/s, HOME_LATCH_VEL=-0.5 mm/s, HOME_OFFSET=-5 mm, HOME=0, and HOME_FINAL_VEL=2 mm/s, in X→Y→Z order. Inputs remain GPIO020/021/022, active-high with five-cycle debounce, connected to each joint's home and negative limit; positive limits remain. Post-homing soft limits are X 0–410, Y 0–265, Z 0–80 mm.

Previously, HOME ALL logical X motion triggered GPIO021 / joint1 and `joint 1 on limit switch error`, consistent with the now-confirmed swapped XY motor channels. Masking another joint's limits is not a fix; v4 migrates output, feedback, enable, and stepgen parameters together. Z homing downward follows the user's physical installation; the operator must ensure no tool, workpiece, or fixture interference below.

## Release and configuration upgrade

The user requested testable automatic homing in v4 and will update manually. Updating never enables, homes, jogs, or starts the spindle automatically. Actual homing completion and distance accuracy await onsite acceptance after updating; these jog observations establish only mapping/polarity provenance.

Fixed postinst bytes remain unchanged. `provision` performs a one-time migration only for installed v1 configuration matching per-file hashes. It requires absent control socket/native lock and validates installed HOMEMOD ABI, hash, and direction-adaptation marker. Write all new configuration to a private same-filesystem temporary directory before atomic exchange; never publish partial INI/HAL on failure. Repeated upgrades verify new hashes without swapping channels again. Unknown configuration, extra files, or manual edits reject migration. Parameters, tool tables, programs, and work offsets are not automatically rewritten; recheck machining coordinates after first homing.

Ordinary prepare still does not claim measured motor verification. Only this migration matching the exact onsite record sets motor-verification flags; configuration records `motionAcceptance=pending-after-update`.

The paired Mesa v4 snapshot remains unchanged. In a temporary build directory, the application adapter makes homing validate search direction/opposite limits using HOME_OFFSET sign, supporting both original reference and this all-negative configuration. Fifty-four public API scenarios cover double triggering, backoff, initially active switches, missing/stuck switches, abort, wrong direction, and opposite limits. Binary provenance records adapter SHA-256. All builds/source regressions run only in GitHub CI.

## Onsite diagnostic boundaries

The agent sent no jog, HOME, spindle, or machining commands; the user supplied onsite observations. Old light-locker obscured the CNC window; terminating that lock-screen process restored display. At user request, permanent sleep/standby fixes were deferred to v5 after feedback.

Real-time timeout investigation: target PREEMPT_RT kernel, servo SCHED_FIFO/98, and memory-lock permission were normal. With the core stopped, cyclictest ran 120000 cycles on CPU3 at 1 ms, with maximum wakeup latency 16 µs. Three hundred Mesa network probes had no loss and maximum round trip 0.217 ms. During two minutes after normal restart, Mesa packet errors stayed zero and the timeout did not recur; concurrent user jogging produced a Z limit alarm. This does not establish resolution of the intermittent timeout's root cause; restarting or clearing historical counters is not a permanent fix. HAL time/tmax are x86 CPU clock counts, not nanoseconds.
