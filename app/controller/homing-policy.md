# Dedicated-appliance homing configuration contract

This defines valid configuration read by Controller through the public LinuxCNC INI API, not a machine measurement record. Configuration generators must validate commissioning JSON; packaged migration accepts explicit measured three-axis travel before selectively updating existing configuration. On 2026-10-26 the user supplied X420/Y275/Z90 mm, allowing preparation of the configuration below. Confirmed parameters do not mean deployment or motion acceptance is complete. Homing remains forbidden without measurements.

## HOME ALL and motion permission

Joints with omitted `HOME_SEQUENCE` or positive values above 100 do not participate in HOME ALL. Negative values retain native synchronized-group semantics; order by absolute value. The first sequence must be 0 or 1, without later gaps. Controller rejects empty/gapped sets before sending commands, preventing indefinite UI waits after native sequencing ends early. Valid immediate single-joint homing remains available for ordinary LinuxCNC configurations without switches/search velocity.

Controller adds:

- `homeAllJoints`: joint indices configured for HOME ALL.
- `homeAllHomed`: all raw `homed` bits in this nonempty set are true; this is not motion permission.
- `homingConfigured`: valid HOME ALL set satisfying applicable appliance policy.
- `homingMessage`: explanation of missing required appliance configuration.

`machine.home-all` waits only for this set; `machine.unhome-all` still waits for all joints to unhome. The full `homed` array retains real per-joint state. MDI, automatic machining, and world-coordinate jog do not ignore ABC after XYZ HOME ALL; the appliance still requires every active joint truly homed. The user confirmed XYZ-only hardware, so explicit migration removes unused template ABC joints, leaving three active joints. Real XYZ completion then satisfies existing motion gates without fabricating ABC state.

## Valid Zhulong V2 INI

Any of `BETTERCNC_KIOSK=1`, `[EMCMOT] HOMEMOD=zhulong_homing`, or `[BETTERCNC_HOMING] PROFILE=zhulong-v2` enables strict policy. Missing configuration rejects all HOME requests without changing ordinary LinuxCNC immediate-homing semantics. Appliance `NO_FORCE_HOMING=1` is a configuration error, not an interlock bypass.

Before enabling, all must hold:

- `[EMCMOT] HOMEMOD = zhulong_homing`, `[TRAJ] LINEAR_UNITS = mm`.
- `[BETTERCNC_HOMING] PROFILE = zhulong-v2`.
- `[BETTERCNC_HOMING] SWITCH_INPUTS_VERIFIED = YES`.
- `[BETTERCNC_HOMING] TRAVEL_X_MM`, `TRAVEL_Y_MM`, `TRAVEL_Z_MM` are finite measured values greater than 15. They mean total usable inward travel from each switch, not the 5 mm backoff.
- Known trivkins mapping X→joint 0, Y→joint 1, Z→joint 2; HOME ALL is exactly `[0, 1, 2]`.
- All axes use `HOME = 0`; `HOME_OFFSET` is `-5, +5, -5`, `HOME_SEQUENCE` is `1, 2, 3`.
- `HOME_SEARCH_VEL` and `HOME_LATCH_VEL` directions are negative, positive, negative; `0 < abs(latch) < abs(search) <= 5`, `0 < HOME_FINAL_VEL <= 5`.
- All use `HOME_IGNORE_LIMITS = YES`, `HOME_USE_INDEX = NO`.
- For measured total travel L, X/Z AXIS and JOINT soft limits include zero, are nonempty, and lie within `[0, L-10]`; Y lies within `[-L+10, 0]`. Preserve narrower existing safe ranges; never widen limits merely to pass validation.

Under strict policy, only joints 0/1/2 may HOME. ABC without a defined plan should use `HOME_SEQUENCE = 101` and cannot masquerade as this feature through single-axis HOME. Even valid complete configuration only permits explicit user homing requests; connection, upload, installation, and startup do not trigger motion.

This contract checks enabled INI only. Packaged integration separately verifies HAL GPIO wiring, debounce scheduling, provenance/version, and module installation. Controller neither imports appliance/HOMEMOD internals nor operates HAL directly.

Packaged public entry: `betterlinuxcnc-appliance stage|prepare --source-config <original-launcher.json> --zhulong-homing-travel-mm 420 275 90 --zhulong-xyz-only`; stage additionally requires `--destination <new-directory>`. It updates only homing fields/required HAL wiring; AXIS/JOINT limits become `[0,410]`, `[-265,0]`, `[0,80]`. Z positive points inward after homing. Parameters, PID, step timing, spindle, and other wiring remain.

`--zhulong-xyz-only` explicitly removes reviewed ABC INI sections and complete old PID/stepgen/HALUI wiring; reject unknown/incomplete ABC patterns. Set JOINTS to 3 and kinematics/coordinates/display geometry to XYZ, retaining board `num_stepgens=6`. Preserve parameter/tool files. New machine coordinates are inward-positive X/Z, inward-negative Y; after actual homing, verify G54 and other work coordinates onsite instead of assuming old values are validated machining coordinates.

GPIO020/021/022 `.in` signals pass through five servo cycles of debounce into X-negative, Y-positive, Z-negative home/limits; retain opposite limits. prepare requires matching installed core/development 2.9.10, HOMEMOD provenance/hash, and six key native header hashes; stage creates a copy pending install checks. Mutually exclusive `--zhulong-inputs-only` wires only verified switches, keeps original homing parameters, sets `motion.homing-inhibit=true`, and neither enables HOMEMOD nor authorizes HOME in Controller.
