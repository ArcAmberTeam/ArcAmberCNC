# Local control protocol v2

The endpoint uses AF_UNIX stream. Its parent is a same-user 0700 directory and the socket is 0600; the service does not overwrite an existing socket. Each frame has a four-byte unsigned big-endian length followed by UTF-8 JSON, with a maximum body of 65,536 bytes. Reject duplicate JSON fields, non-finite numbers, invalid versions, unknown fields, invalid arguments, and oversized frames.

v1 retains the old `{version:1, request_id, method:"health"}` format, returning historical diagnostics and `machine_connected:false`. It neither obtains a control session nor represents actual machine state; the independent `tools/diagnostics` library retains compatibility.

v2 request:

```json
{"version":2,"request_id":"unique-id","method":"session.status","params":{"jog_lease":false}}
```

Success returns the same version/request_id and a `result` object; failure returns `error:{code,message}`. Never reuse request_id on a connection. Clients do not resend commands automatically; losing an acknowledgement after sending means outcome unknown.

| Method | Parameters | Result |
| --- | --- | --- |
| `machine.status` | Empty object | Independent read-only operating state, motion/task execution lines, tool, spindle, coolant; no attached control session required |
| `session.attach` | Optional `ini_path` | Snapshot; reject INI mismatch or an existing owner |
| `session.status` | Optional boolean `jog_lease` | Latest machine snapshot; only an established jogging lease can be renewed |
| `command.execute` | `action`, object `payload` | `accepted` and `snapshot`; accepted does not mean completed |
| `preview.start` | Absolute `path` | `job_id`; service obtains context, which clients cannot replace |
| `preview.read` | `job_id`, nonnegative integer `offset` | Up to 256 segments, next_offset, busy, done, units, bounds, error, warnings, truncated |
| `preview.cancel` | `job_id` | `cancelled:true` |

Except for `machine.status` and `session.attach`, each v2 method requires the current connection to own the session. `machine.status` reads `linuxcnc.stat` through independent `StatusReader` on the worker thread, without command/error channels, control ownership, or jogging renewal; it remains available without a desktop session. There is at most one control owner, with one preview task belonging to that connection. Control disconnect releases ownership and cancels preview/unsent subsequent commands. Observer disconnect does not change machine state. Other LinuxCNC tools are not constrained by this socket's ownership and must be coordinated at deployment.

In `machine.status`, `currentLine` comes only from `motion_line`, `taskLine` from task `current_line`, and `readLine` from interpreter lookahead `read_line`. Return these separately; task/lookahead lines must not replace motion execution lines. `progressPercent` stays null: loops, subroutines, and different segment durations prevent line numbers from expressing accurate completion. `programState` is idle/running/paused/busy/estop/off/unknown; idle does not prove a job succeeded. See the [CAM integration protocol](cam-link-protocol.md) for the external interface.

`machine.status` also returns `busy` when interpreter, execution state, or queue has not settled; `velocity` in native units/second, null if absent/non-finite; and `nativeCommandState`, normalizing NML `stat.state` RCS_DONE/RCS_EXEC/RCS_ERROR to done/executing/error, otherwise unknown. `nativeCommandState` is only a native-channel observation, not completion of a GUI request. If the service still tracks an accepted/pending/sent/unknown desktop command, it additionally returns that request's `commandState`; do not confuse them. The updater must confirm fresh native state, queue, and request state permit shutdown, followed by normal launcher exit. Read-only observation cannot replace physical machine interlocks.

`machine.status.configuration` is read-only machine configuration, null when unavailable/offline; older services may omit it. Format: `{schemaVersion:1, axes:[...], kinematics:string|null}`. Axes follow `XYZABCUVW` order and include only those actually enabled in NML `axis_mask`, never inferred from joint count or reserved INI sections. Configuration comes from the running instance's `ini_filename`, using the LinuxCNC INI reader for includes.

Each axis has `name`, `kind` (linear/rotary), `unit` (mm/deg), `min`, `max`, and `maxVelocity`. ABC are rotary; others linear. Soft limits come from `AXIS_<name>.MIN_LIMIT/MAX_LIMIT`, converted from native units to millimeters/degrees; `MAX_VELOCITY` is converted to units per minute. Unknown/invalid values are null; inverted bounds make both null. Soft limits use machine coordinates and cannot directly bound toolpaths in work coordinates or represent total mechanical travel. `kinematics` is INI `KINS.KINEMATICS`, at most 256 characters, without the configuration path. Four/five axes do not establish simultaneous four/five-axis machining support; clients must not infer rotary centers or automatically select kinematic models.

## State and operations

`connected` means LinuxCNC status is valid; Qt separately maintains `serviceConnected`. Do not conflate them. Position arrays follow `XYZABCUVW`; lengths/angles use native LinuxCNC units. `linearUnits` is native units/mm; `angularUnits` is native units/degree. Joint numbers are independent of axes; do not guess unknown kinematic mappings. Preview XYZ output always uses millimeters.

The complete tool table remains in the service for preview; wire snapshots identify changes through `toolTableRevision`. Wire error history retains the latest 20 entries, each at most 1024 UTF-8 bytes, with errorHistoryCount/errorsTruncated, preventing large tables/errors from overflowing frames.

`commandState` is idle, pending, sent, completed, error, or unknown. pending may still await mode switching; sent awaits LinuxCNC acknowledgement; completed confirms that command, **not completion of the whole machining program**. Do not send subsequent steps while busy, after conditions change, or when an external writer advances acknowledgement.

| action | payload |
| --- | --- |
| `machine.estop`, `machine.power` | Optional enabled; otherwise toggle using fresh state |
| `machine.mode`, `motion.mode` | mode: manual/mdi or joint/world |
| `machine.debug` | Integer value 0–2147483647; await stat.debug confirmation |
| `machine.home`, `machine.unhome` | Explicit joint; use machine.home-all for all joints |
| `jog.start` | axis character or explicit integer joint, mode, direction ±1, velocity in native units/second, increment in native units |
| `jog.stop` | Empty object; cancel unsent start and stop this session's jogging |
| `mdi.execute` | Single-line text, maximum 254 bytes |
| `program.run`, `program.step`, `program.pause`, `program.resume`, `program.stop` | Empty object; program.run-line takes a one-based line |
| `spindle.cw`, `spindle.ccw` | Optional RPM speed; explicit speed required without configured default |
| `spindle.stop`, `spindle.increase`, `spindle.decrease`, `spindle.brake` | Brake may include enabled |
| `coolant.flood`, `coolant.mist` | Optional enabled |
| `override.feed`, `override.rapid`, `override.spindle`, `velocity.max` | value as ratio or native units/second |
| `machine.touch-off`, `tool.touch-off` | axis, value in native units, system, target |
| `file.open` | Absolute path |
| `file.save` | Absolute path, text; service writes then requests load |
| `tool.reload`, `tooltable.save` | Reload is empty; save takes text, with path from actual INI |

Capabilities advertise availability, but Controller always validates conditions. Program/tool editing text is limited to 60,000 UTF-8 bytes and the overall JSON frame limit. Reject excess rather than truncating; never complete deferred writes or replay after disconnect.

The Qt GUI sends a timestamp to the socket worker every 100 ms. After 350 ms without heartbeat, the client requests jogging stop and ceases renewal. The nominal service lease is 600 ms; native NML commands may hold the GIL while awaiting acknowledgement, so this is not a hard real-time stopping bound. Stop, exit, focus loss, and UI release must cancel current jogging. Automatic reconnect must never restart jogging.

The preview subprocess uses temporary parameter/INI copies, no stdin, and interpretation/collection timeouts. It may create read-only stat to initialize tooldata, never command/error channels. Crashes, interpretation errors, excessive results, and unsupported execution extensions return explicit errors rather than fabricated toolpaths. See [Qt migration notes](qt-qml-migration.md) for operation and unaccepted scope.

## Service-owned CAM machining jobs

With explicit service `--cam-inbox`, unattached connections may call `cam.job.start` and `cam.job.status`, each requiring only `{transferId}`. The service reuses its Controller and single serial worker. These interfaces accept only validated inbox files, not client paths or arbitrary machine commands. See [CAM protocol](cam-link-protocol.md) for state, deduplication, and interlocks. Desktop sessions and CAM jobs can share one Controller; desktop disconnect cancels only its preview, jogging, and unsent desktop actions, not service-accepted CAM jobs. Service shutdown still cancels unsent job steps without automatically aborting running machining; restart does not replay.

## Shared CAM and desktop jogging controller

`cam.jog.start` takes `{jogId,axis,direction,feedRate}`: axis X/Y/Z, direction ±1, and positive feedRate within 0–3000 mm/min. `cam.jog.keepalive` and `cam.jog.stop` take `{jogId}`. These methods do not acquire desktop `session.attach` ownership and execute serially through the same existing Controller. The service converts speed using fresh machine length units.

A jog is bound to its Unix connection and UUID, with an independent 600 ms lease. Disconnect, stop, or expiry revokes it immediately; queued old starts must not execute. Desktop status heartbeats cannot renew CAM jogging. Reject remote starts during local jogging; remote jogging rejects other motion commands, while local emergency stop, power-off, program stop, and jog stop can revoke it. CAM automatic machining cannot start within a jogging lease. Reject duplicate UUIDs within the five-minute retention window, capped at 4096 entries. Desktop exit and service shutdown also revoke jogging; polling, file receipts, and ownership of accepted machining retain their existing rules.
