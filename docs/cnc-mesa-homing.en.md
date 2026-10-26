# Homing

> English companion translation of [the pinned vendor document](../vendor/cnc-mesa/docs/homing.md). The original snapshot and its checksums remain unchanged. Historical commissioning notes below retain their original scope; later version sections record subsequent changes.

Inputs 20/21/22 correspond to X/Y/Z. The user most recently confirmed normally closed switches to GND: conducting when untouched, open when actuated. Use `.in`, normal 0 and triggered 1. Board `homing.active_low=false` selects `.in`; only verified active-low configurations use `.in_not`. After five servo cycles of debounce, connect both home and the corresponding directional limit.

Reference sequence: search in the calibrated homing direction; stop on trigger; retreat inward 5 mm from the first trigger position; approach slowly for a second trigger; retreat inward 5 mm to final machine coordinate zero. Board homing.distance_mm determines backoff. Actual repeatability depends on switches, debounce latency, and following error.

The latest physical definition is X forward/back (420 mm), homing backward; Y left/right (275 mm), homing left; Z up/down (90 mm), homing downward. This replaces earlier X left/right and Y forward/back descriptions. Old X−/Y+/Z− reference signs retained in code were not calibrated to this definition and are not directly executable machine configuration. Photos cannot convert physical directions into motor/machine-coordinate signs.

Standard LinuxCNC first backoff normally stops after switch release; this module performs full fixed-distance backoff. HOME_OFFSET defines the second trigger coordinate and HOME=0 the final return. LinuxCNC still owns trajectories, acceleration/deceleration, cancellation, and coordinates; FPGA never independently bypasses it to emit pulses.

Settings: linuxcnc/homing.json. search_speed_mm_s is initial search, latch_speed_mm_s second slow search, return_speed_mm_s final return. Set switch_inputs_verified=true only after checking physical labels and untouched/triggered/released states for all axes. usable_travel_from_switch_mm is measured total usable inward travel from each switch. Generic templates retain null; machine instances use their own confirmed measurements, here X420/Y275/Z90 mm. The existing 5 mm backoff is not total travel. The generator reserves one backoff at each end and generates signed soft limits; span must exceed backoff, so each total travel must exceed 15 mm.

Switch verification does not establish motor output mapping/polarity. Onsite evidence reported logical X / stepgen.00 moving physical Y and triggering GPIO021, with other channels still unverified. Application backend must reject HOME/HOME ALL until all motor mappings/directions are explicitly accepted, regardless of travel, switch checks, or generator success. See [LinuxCNC integration handoff](cnc-mesa-linuxcnc-integration-handoff.en.md).

GitHub CI build, using the package's LinuxCNC development environment:

    make prepare-homing
    cd .build/homing
    halcompile --compile zhulong_homing.comp
    cd ../..
    make test-homing

CI includes the module in the release DEB. Targets install DEBs only, without onsite compilation/manual runtime-configuration edits. See [integration handoff](cnc-mesa-linuxcnc-integration-handoff.en.md) for integration/status.

Standalone reference generation: `python3 linuxcnc/prepare.py --settings /path/to/verified-homing.json --output /path/to/empty-directory`. Defaults intentionally cannot enable homing. Files are written only with verified inputs/complete measured travel; nonempty destinations are rejected. Generated vendor motion parameters must not overwrite tuned machines. Integrators selectively merge homing fields per handoff. HOME ALL order is X, Y, Z; undefined A/B/C homing is excluded.

Verification exercises public HOMEMOD APIs using LinuxCNC single-axis trajectory planning to simulate motion and check state, distance, faults, and cancellation. Software tests do not establish physical homing acceptance.

## v26.10.26.5 signed and parallel profile

The HOMEMOD now derives the search direction and opposite-limit selection from the sign of HOME_OFFSET. The original generator remains a conservative commissioning reference; it must not overwrite an installed, tuned machine profile. The application owns the exact reviewed v1/v4 migration.

The operator confirmed stepgen.01=X (positive forward), stepgen.00=Y (positive right), and stepgen.02=Z with negative STEP_SCALE (positive up). The installed v5 profile homes all axes in the negative direction: X back, Y left, Z down, with independent GPIO020/021/022 inputs. Travel is 420/275/90 mm. HOME stays 0 and HOME_OFFSET stays -5; minimum soft limits become -0.1 mm, giving feedback quantization margin while staying 4.9 mm inside the switch. Maximum limits remain 410/265/80 mm.

Public HAL input `joint.N.home-backoff-vel` is a positive speed in machine units/second, default 2. It is sampled and validated at HOME_START, then remains fixed for that attempt. XYZ accepts values greater than zero and at most 2; invalid/non-finite values abort the entire request. It controls both initial switch clearance and the full first retreat, independently of HOME_SEARCH_VEL. The standard C HOMEMOD API remains unchanged.

The v5 application sets XYZ HOME_SEQUENCE=1 for concurrent independent homing. Search is X/Y -15 and Z -5 mm/s; first backoff is +2; latch is -1; final retreat to HOME is X/Y 5 and Z 2 mm/s. Failure or cancellation clears homed state and disables every planner in the current request, including peers that already finished. Other requests and unrelated previously homed joints are not touched.

The public API harness covers both signed reference profiles (54 scenarios) and parallel operation (27 scenarios). The parallel harness uses the LinuxCNC planner at 750 mm/s², 1 ms steps and five complete periods of input delay. It measures peak penetration and checks a 0.5 mm software budget within the operator-reported minimum 1 mm switch overrun. These results do not verify real motor deceleration, step loss, latency or collision clearance. The first physical parallel test requires no tool, an empty table, and a verified collision-free full XYZ envelope including downward Z. Machine acceptance remains pending; CI never starts hardware.
