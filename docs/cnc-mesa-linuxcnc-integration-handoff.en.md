# Zhulong V2 homing integration handoff

> English companion translation of [the pinned vendor handoff](../vendor/cnc-mesa/docs/linuxcnc-integration-handoff.md). The original snapshot and its checksums remain unchanged. Paths below refer to the CNC-Mesa source repository unless explicitly stated otherwise. Historical records and later v5 updates retain their original order and scope.

Delivered to the Evaluate Project Architecture Characteristics task handling LinuxCNC packaging/target integration. Subsequent user convention: CNC-Mesa commits directly on existing main; ArcAmberCNC uses existing kihon PRs to main, with the integration task replacing original PR #27. All commit emails are IwakuraTorei@outlook.com. Build/test only in GitHub CI, then install after merge/Release DEB. No new branches, local/target compilation/tests, direct target-configuration edits, or installation-triggered homing/jogging/FPGA flashing.

## Known information and evidence

| Item | Current evidence |
| --- | --- |
| Wiring | Latest user confirmation: mechanical NC, input through switch to GND; conducting untouched, open when actuated |
| Axis inputs | User specifies GPIO 20=X, 21=Y, 22=Z; HostMot2 GPIO numbers, not physical DB25 pins |
| Latest physical axes | User photos/observations: X forward/back, 420 mm; Y left/right, 275 mm; Z up/down, 90 mm, replacing earlier X left/right and Y forward/back |
| Physical homing | X backward, Y left, Z down; machine/motor signs still need calibration, not inference from photos/old configuration |
| Polarity | Raw .in: untouched 0, triggered 1, released 0; software-inverted .in_not is unused |
| Backoff | Existing 5 mm module parameter for first retreat and retreat after second touch |
| Total travel | User-confirmed usable switch-to-opposite-end X420/Y275/Z90 mm; generic template stays null, never inherits a machine's measurement |
| Motor mapping | Onsite verification incomplete; logical/physical mismatch observed below. Correct GPIO mapping does not prove motor-output mapping |

Factory `docs/hardware/烛龙V2 使用说明 必看.doc` shows GPIO—switch—GND only, without internal inversion or NC/NO terminal labels. Polarity here relies on latest user wiring/runtime readings. HostMot2 .in_not inversion is implemented in LinuxCNC src/hal/drivers/mesa-hostmot2/ioport.c.

Initial read-only audit on 2026-10-26, before HOMEMOD integration: GPIO020/021/022 were inputs, stationary .in=FALSE/.in_not=TRUE. Running three-axis home-sw and positive/negative limit signals had joint receivers but no GPIO writer; INI lacked search/latch velocities and zhulong_homing. Thus changing GPIO without joint home/limit changes meant unwired signals, not failed switch detection.

Subsequent manual-switch evidence from the integration task, target logs UTC 19:12–19:14 at about 100 ms sampling:

- All three showed quick FALSE→TRUE→FALSE taps.
- GPIO021 repeated long holds around 1.34–1.44 s; user confirmed the same Y switch, with no sampled interruptions.
- GPIO022 holds around 1.03/1.96 s and GPIO020 around 1.34/1.44 s remained stable in samples and returned FALSE on release.
- Later user confirmation identified another GPIO020 hold around 6.914 s as X and the prior two GPIO022 holds as Z. All physical labels/active-high polarity were checked. Sampling at 100 ms cannot exclude millisecond contact bounce; retain servo debounce.

Generic switch_inputs_verified remains false to prevent new installations inheriting old acceptance. Integrators may record true and confirmed travel for this specific machine; that verifies inputs/travel only, not motor mapping or permission to enable homing.

## Motor mapping and direction prerequisites

The integration task reported that earlier onsite HOME ALL logical X / stepgen.00 actually moved the physical 275 mm Y axis, then GPIO021 triggered. This exposed logical/output/physical mapping errors. User photos subsequently clarified the physical definitions above. Other channel-to-axis mappings and signs were unverified; do not infer that merely swapping XY suffices or guess Z channel/polarity.

zhulong_homing and HAL/INI tables below assume joint.0/1/2 drive actual X/Y/Z. With wrong mapping, assigning logical X travel 420 mm cannot protect the actual 275 mm Y being driven. Correct switches/simulation do not prove mapping.

Old reference uses logical X−/Y+/Z− and was not calibrated to latest backward/left/down directions, so it is not currently executable. Do not assign backward to X+/- or infer Z motor sign from downward. HOMEMOD validates that old convention; different onsite signs require confirmed mapping, consistent module/configuration adaptation, and CI, not trial-and-error HOME parameter/pin flips.

Application integration must separately record switch checks, measured travel, motor-channel/physical-axis mapping, and sign verification. Any unconfirmed mapping/direction makes the backend reject both single HOME and HOME ALL with specific UI reasons. Lift restrictions only after explicit onsite records and matching configuration, never from switch_inputs_verified=true, old homed flags, version upgrades, or existing INI.

This paired version retains HOMEMOD, VHDL, pins, and motion directions. Application owns machine-level motor mapping/sign gates. The reference generator validates declared inputs/directions/travel but does not measure/prove motor connections and cannot alone authorize enabling. Onsite verification/configuration changes follow published application updates, not temporary target patches, automatic pin swaps, or flashing experiments.

## Source and public interfaces

Local source: `/Users/goodgirlkihon/Documents/CNC-Mesa`. Handoff messages provide pinned commit/archive SHA-256. Include that attributed third-party snapshot in the existing PR rather than depending on target source directories.

| Path | Purpose and boundary |
| --- | --- |
| homing/zhulong_homing.comp | Public HAL entry, option homemod, module zhulong_homing |
| homing/prepare.py | Inlines adjacent src/homing.c into .build/homing/zhulong_homing.comp; no build/install |
| homing/src/homing.c | Standard LinuxCNC homing API/joint trajectory planner, no direct FPGA driving |
| homing/provenance.json | Original commit/file hashes/change scope, preserving GPL headers/provenance |
| mesa/board/zhulong-v2.json | Public board GPIO, direction, backoff, active_low=false |
| linuxcnc/homing.json | Commissioning speed, switch verification, pending travel template |
| linuxcnc/prepare.py | Public prepare(settings, destination, *, board_path=...) and CLI for standalone vendor references |
| tests/test_linuxcnc_config.py | Public generator polarity/routing/order/input/no-overwrite/CLI tests |
| tests/homing/test_homing.c, homing/upstream/simple_tp.*, tools/test_homing.py | 27 public HOMEMOD XYZ normal/fault/cancel scenarios without hardware |

Minimal builds need only homing/. Tests/configuration integration also need other listed files, linuxcnc/vendor-reference/, and root Makefile. Vendor references are generator-test inputs and must not overwrite /etc/betterlinuxcnc/machine. No FPGA bitstreams, HostMot2 HDL, or flashing tools need importing.

## GitHub CI and DEB

Run on GitHub with the Release core's matching LinuxCNC headers, RTAPI types, and architecture:

```sh
make prepare-homing
cd .build/homing
halcompile --compile zhulong_homing.comp
```

halcompile must come from the Release LinuxCNC build environment; it locates headers through its Makefile.modinc. Never insert a .so prebuilt for another core version.

Install zhulong_homing.so in that LinuxCNC real-time module directory beside homemod.so/motmod.so, determined from actual EMC2_RTLIB_DIR/package lists, not another prefix. Verify the DEB contains it, with correct architecture/dynamic dependencies. Preparation/test code need not install to target runtime directories.

Current test entries:

```sh
# Complete snapshot: provenance/module boundaries, Python regressions, HDL mapping, HOMEMOD
make check test-hdl test-homing

# Minimal homing snapshot: configuration, actual HOMEMOD compilation/public API simulation
python3 -m unittest discover -s tests -p test_linuxcnc_config.py -v
make test-homing
```

Complete checks require Python3, GHDL, make, gcc, and LinuxCNC development packages. Minimal checks need no GHDL. test-homing first actually runs halcompile --compile, then three axes × nine cases: normal, initially triggered, never triggered, no release after first trigger, no release after second, cancel search, cancel backoff, opposite limit, and wrong direction. All are CI simulations without real controllers.

No local builds/source tests were run for this handoff. Results come from existing PR GitHub CI; repair/retry snapshot/integration failures without claiming physical acceptance.

Root release.json defines versions, currently paired v26.10.26.4. After pushing the matching tag, CI must pass all checks before source/minimal-integration archives, mesa-release.json, and SHA256SUMS publish. Manifest includes board/variant/source commit/application version/archive hashes/firmware availability; mismatched source/application versions reject generation.

No new bitstream is proven built from this source and board-verified, so firmware.available=false, asset/sha256/size=null, origin=unavailable, and verification.implementation/timing/board_approved=false. Independent Rust updating may discover/download paired source/metadata but must report no flashable firmware. Never extract a factory reference .bit and claim it as new. Future bitstreams need ISE build, constraints/timing, board verification, and separate artifact rules requiring origin=ci-build and true acceptance fields.

## VHDL delivery

Existing firmware/zhulong-v2/PIN_ZHULONG_V2_34.vhd leaves 20/21/22 as ordinary GPIO (IOPortTag + NullTag), with six STEP/DIR mappings unchanged. hostmot2/upstream/hostmot2.vhd uses original WordPR for direction/output and WordRB for raw input; output inversion does not affect input readback. No FPGA homing state machine, polarity change, or new bitstream flashing is needed.

Added tests/hdl/nc_inputs_tb.vhd directly instantiates unmodified Mesa wordpr.vhd/wordrb.vhd for actual two 17-bit ports, checking 20/21/22 default input high impedance, closed 0, open 1, hold/release, simultaneous triggers, cross-port isolation, unselected-bus high impedance, and output inversion independence. Existing board_profile_tb.vhd still checks all 34 pins/six stepgens.

Run python3 tools/test_hdl.py in GitHub CI. Minimal HDL snapshot includes tools/test_hdl.py, tests/hdl/*.vhd, firmware/zhulong-v2/PIN_ZHULONG_V2_34.vhd, and upstream IDROMConst.vhd, i92_x9card.vhd, wordpr.vhd, wordrb.vhd, preserving copyrights/original hashes. Simulation checks digital logic, not analog board circuitry, full ISE timing, or reconstruction of vendor bitstreams.

## Selective configuration merge

Integration owns persistent /etc/betterlinuxcnc/machine INI/HAL and mutable /var/lib/betterlinuxcnc/machine. Use existing package backup/upgrade-migration/rollback flows; do not wholesale import vendor INI/HAL. Audit once observed `/home/teto/ArcAmberCNC/configs/zhulong-v2/烛龙V2.ini`; confirm actual files from launcher/process arguments when integrating.

1. Module installation may happen first. Homing enablement requires all switch checks, measured travel, motor/physical-axis mapping, polarity verification, and installed module. Otherwise report specific missing conditions such as unverified motor mapping at the control entry. Never fall back to switchless immediate zeroing or treat HOME_SEARCH_VEL=0 as usable for this feature.
2. Merge only homing fields/signals below. Preserve stepgen pins, pulse timing, SCALE, speed/acceleration, PID, enables, emergency stop, spindle, kinematics, display, and network services.
3. Inspect actual HALFILE lists and all home/limit connections. Never silently overwrite existing writers, duplicate debounce instances, different GPIO mappings, or wired opposite limits. Keep originals/report conflicts on failure.
4. Validate temporary copies before package migration. Update INI/HAL together, idempotently, without repeated loadrt/addf/net. Unknown conditions permit module installation and disabled templates only, not loading/calling homing.

### HAL merge points

Signals/signs below describe old references, not calibration to latest physical definitions. Application homing remains disabled until motor channels/directions are accepted.

Load debounce and schedule after hm2_7i92.0.read, before motion-command-handler/motion-controller. If debounce exists, allocate unused channels/rename appropriately; do not load twice.

```hal
loadrt debounce cfg=3
setp debounce.0.delay 5
# Insert into existing servo-thread scheduling, not simply at the end of the file:
# addf hm2_7i92.0.read servo-thread
addf debounce.0 servo-thread
# addf motion-command-handler servo-thread
# addf motion-controller servo-thread

net x-home-raw hm2_7i92.0.gpio.020.in => debounce.0.0.in
net y-home-raw hm2_7i92.0.gpio.021.in => debounce.0.1.in
net z-home-raw hm2_7i92.0.gpio.022.in => debounce.0.2.in

net x-home-sw debounce.0.0.out => joint.0.home-sw-in joint.0.neg-lim-sw-in
net y-home-sw debounce.0.1.out => joint.1.home-sw-in joint.1.pos-lim-sw-in
net z-home-sw debounce.0.2.out => joint.2.home-sw-in joint.2.neg-lim-sw-in
```

Reuse existing signals such as net x-home-sw => joint.0.home-sw-in rather than redefining. Move corresponding old empty x-neg-limit/y-pos-limit/z-neg-limit receivers to the home signal; retain opposite limits. Never set GPIO to outputs. Five-cycle debounce duration depends on servo period, approximately 5 ms at 1 ms.

### INI merge points

```ini
[EMCMOT]
HOMEMOD = zhulong_homing
```

LinuxCNC loads HOMEMOD before motion HAL; do not loadrt zhulong_homing again in HAL. Confirm no startup -m override.

| Field | JOINT_0 / X | JOINT_1 / Y | JOINT_2 / Z |
| --- | ---: | ---: | ---: |
| HOME | 0 | 0 | 0 |
| HOME_OFFSET | -5 | +5 | -5 |
| HOME_SEARCH_VEL | -2 | +2 | -2 |
| HOME_LATCH_VEL | -0.5 | +0.5 | -0.5 |
| HOME_FINAL_VEL | 2 | 2 | 2 |
| HOME_SEQUENCE | 1 | 2 | 3 |
| HOME_IGNORE_LIMITS | YES | YES | YES |
| HOME_USE_INDEX | NO | NO | NO |

HOME_IGNORE_LIMITS=YES applies to shared homing-direction limits; the module still aborts on opposite limits. Uninstalled opposite switches are not existing hardware protection. Undefined ABC uses HOME_SEQUENCE=101 to exclude HOME ALL; individual ABC homing cannot masquerade as this XYZ capability.

For measured usable inward travel L and backoff d=5, reserve d at both ends, span S=L−2d, requiring L>3d. Under old signs, X/Z AXIS/JOINT limits are [0,S], Y [-S,0]. This reference strategy was not accepted for the new physical definition. Verify signs/travel before integration and never widen legal existing limits to bypass checks. Unknown/insufficient travel rejects enablement; do not use test value 200 mm.

Confirmed X420/Y275/Z90 yields spans X410/Y265/Z80 mm, but signed intervals await calibration. Only onsite verification of old X−/Y+/Z− permits X [0,410], Y [-265,0], Z [0,80]. These signed references or Z− cannot currently authorize the new physical definition or lift homing gates.

## Control entry and acceptance

CAM/Rust/desktop use existing LinuxCNC HOME through the control layer and standard joint homing API. Until all axes/configuration are ready, backend must reject, not merely disable frontend buttons. CAM connection, upload, and package startup never home automatically.

Sequence: search confirmed direction → stop on first trigger → full 5 mm inward retreat → slow second trigger → another 5 mm inward retreat → machine coordinate zero and homed. Initially active switches first clear then search. Failure to release, wrong distance, cancellation, or abnormal limits must not report homed.

First verify software: packaged module, idempotent migration, rejection of unconfigured requests, simulated double touch/fault cancellation. After installation, initially read switches only while disabled/emergency-stopped and confirm raw/debounced/joint home/corresponding-limit agreement. Physical homing is separate after measured travel/onsite readiness. This handoff neither proves physical homing nor authorizes automatic post-install motion.

## v5 interface handoff

Use paired `v26.10.26.5` sources. `joint.N.home-backoff-vel` is a positive HAL input, default 2 mm/s, latched at HOME_START and restricted to (0, 2] for XYZ. Bind the application's HOME_BACKOFF_VEL INI field explicitly using HAL setp; LinuxCNC does not natively parse that custom INI field. The source now handles signed HOME_OFFSET directly; remove the application's C text-replacement direction adapter. Equal positive sequence 1 runs independent XYZ concurrently. Any attempt failure cancels all members, even earlier completed peers.

The exact machine migration is owned by ArcAmberCNC, including confirmed motor mapping, -0.1 mm soft minimum and pending empty-table acceptance. No FPGA update payload is published and no target-side build or source patch is permitted.
