# Bidirectional CAM Link TCP protocol

CAM Link receives external CAM-generated G-code over a persistent TCP connection after protocol handshake and returns receipts, machining-job state, and read-only machine feedback. External protocol version is 2, with readable header types such as `SEND_GCODE` for program transfer. External TCP and internal Unix socket v2 control protocols are independent.

## Module responsibilities

```text
app/platform/cam-link/src/
  lib.rs                 Public system-service entry
  cam_link/
    protocol.rs          CAM2 framing, strict JSON, parameter structures
    inbox.rs             Chunk reception, hashes, private files, atomic receipts
    control.rs           Local v2 Unix protocol adapter
    manual.rs            XYZ jogging and 450 ms network lease
    feedback.rs          Status queries, file association, serialized sending
    discovery.rs         UDP broadcasts and handshake
    session.rs           TCP sessions, dispatch, subscriptions
```

The network service builds as an independent Rust binary without embedded Python. LinuxCNC APIs, single command writer, interlocks, and job persistence remain in local Python Controller. The launcher owns startup order/supervision.

## Startup

Default is direct LAN connection without `--token-file`, `--cert`, or `--key`; CAM discovers a device and connects with one click. The first frame remains `AUTH / session.auth` with `{}` parameters; `authenticated:true` means handshake complete only. Direct mode has no token authentication/encryption, while protocol, SHA-256, machine-interlock, and jogging-lease checks remain. Token/TLS instructions below apply to explicitly configured compatibility mode, never automatic downgrade after authentication failure.

Build/install all modules from repository root:

```sh
cmake -S . -B build -DBUILD_TESTING=OFF -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build --parallel
sudo cmake --install build
betterlinuxcnc-launch --config ./launcher.json
```

Build requires the toolchain pinned by `app/platform/cam-link/rust-toolchain.toml`. Standalone build: `cargo build --manifest-path app/platform/cam-link/Cargo.toml --release --locked`; binary: `app/platform/cam-link/target/release/betterlinuxcnc-cam-link`. Standalone installation uses `cmake -S app/platform/cam-link -B build/services`, then build/install.

Installed command remains `betterlinuxcnc-cam-link`; existing launcher `cam` configuration is unchanged. CMake builds/installs Rust by default, replacing the old Python CLI and removing installed `bettercnc_cam_link`. Python wheels no longer install this command; `python -m bettercnc_cam_link` is unsupported. `BETTERCNC_CAM_LINK_BINARY` can select a prebuilt binary for the same target. `BETTERCNC_BUILD_SYSTEM_SERVICES=OFF` is for Qt-only tests, not full installations.

Local controller/launcher remain Python; the Rust network service itself needs no Python runtime.

Optional authentication uses a current-user-owned 0600 token file with 32–256 letters, digits, underscores, or hyphens, generatable by `secrets.token_urlsafe(32)`. Never pass tokens directly as CLI arguments.

```sh
betterlinuxcnc-cam-link \
  --host 127.0.0.1 --port 6522 \
  --inbox /home/cnc/cam-inbox \
  --token-file /home/cnc/.config/bettercnc/cam-token \
  --control-socket /run/user/1000/betterlinuxcnc/control.sock
```

Default listening is local only. For cross-device connections, set `--host` to the machine's network address. Optional TLS uses `--cert`/`--key`; CAM verifies the certificate then sends the same TCP frames. This port serves the custom CAM Link protocol, not HTTP.

The inbox must be current-user-owned 0700 and is created if absent. Complete programs are `<inbox>/<transferId>/<filename>` with 0600 permissions. Without automatic machining, the local operator selects files; enabled behavior is described below.

Start the local controller separately. Programs can still be received if it is unavailable; machining feedback returns `controller_unavailable`. CAM Link starts neither LinuxCNC nor its controller.

## Discovering machines without knowing their IP

The machine broadcasts UDP so CAM needs no preconfigured IP. Discovery is off by default; enable with:

```sh
betterlinuxcnc-cam-link \
  --host 0.0.0.0 --port 6522 \
  --inbox /home/cnc/cam-inbox \
  --token-file /home/cnc/.config/bettercnc/cam-token \
  --control-socket /run/user/1000/betterlinuxcnc/control.sock \
  --discover \
  --device-id 550e8400-e29b-41d4-a716-446655440000 \
  --device-name CNC-01
```

Use a stable lowercase UUID assigned to this machine at installation as device-id, retained across starts. The example UUID must not be reused across machines. Default direct LAN mode keeps `tls:false` without certificate/key input. Enable optional TLS/token mode only when explicitly configured by existing deployment.

Default broadcasts go to `255.255.255.255:8421` every three seconds; machine UDP listening is also 8421. CAM listens on `0.0.0.0:8421` and retains recvfrom source IP/UDP port. IPv4 broadcasts require `SO_BROADCAST` and cover the local segment, not routed/VLAN discovery. [Linux ip(7)](https://man7.org/linux/man-pages/man7/ip.7.html)

`--discovery-address` selects interface-subnet broadcast, `--discovery-port` CAM listening port, `--discovery-bind-port` machine UDP binding, and `--discovery-interval` 0.1–60 seconds. With multiple interfaces, explicitly choose machine --host and corresponding broadcast. Permit UDP discovery/TCP service traffic; switch/wireless client isolation must not block broadcasts.

Handshake:

```text
Machine -- UDP broadcast ANNOUNCE --> CAM
Machine <-- UDP unicast DISCOVER_REPLY -- CAM
Machine -- UDP unicast DISCOVER_ACK --> CAM
Machine <-- TCP connection + session.auth -- CAM
```

UDP reuses the 24-byte CAM2 header. One datagram contains exactly one frame, at most 1024 bytes, without fragmentation/reassembly or program files. Header/body events must match:

| Header type | Body event | Purpose |
| --- | --- | --- |
| `ANNOUNCE` | `discovery.announce` | Advertise connectable machine service |
| `DISCOVER_REPLY` | `discovery.reply` | CAM replies to a received announcement |
| `DISCOVER_ACK` | `discovery.ack` | Machine acknowledges CAM reply |

Announcement contains no token, program, or machining state:

```json
{"version":2,"event":"discovery.announce","service":"bettercnc-cam-link","deviceId":"550e8400-e29b-41d4-a716-446655440000","deviceName":"CNC-01","tcpPort":6522,"tls":false,"nonce":"0123456789abcdef0123456789abcdef"}
```

CAM unicasts to the announcement's source IP/UDP port, copying deviceId/nonce and adding its own lowercase UUID:

```json
{"version":2,"event":"discovery.reply","service":"bettercnc-cam-link","deviceId":"550e8400-e29b-41d4-a716-446655440000","camId":"3d813cbb-47fb-32ba-91df-831e1593ac29","nonce":"0123456789abcdef0123456789abcdef"}
```

The machine accepts only its own device ID and a recent announcement nonce. ACK echoes camId/nonce unchanged and adds device name, TCP port, and TLS flag:

```json
{"version":2,"event":"discovery.ack","service":"bettercnc-cam-link","deviceId":"550e8400-e29b-41d4-a716-446655440000","deviceName":"CNC-01","camId":"3d813cbb-47fb-32ba-91df-831e1593ac29","tcpPort":6522,"tls":false,"nonce":"0123456789abcdef0123456789abcdef"}
```

CAM connects to the ACK source IP and body tcpPort; device ID, CAM ID, and nonce must match the pending handshake. IP is not declared in JSON; never use `0.0.0.0` or broadcast as TCP target. tls describes listener configuration, not a replacement for CAM's predefined TLS authentication policy.

Retain the latest three announcement nonces, each valid for three broadcast intervals. Silently ignore expired, wrong-device, malformed, or oversized packets. Acknowledge at most eight valid replies per second. On loss/rate limiting, CAM may wait for the next announcement. Broadcasts continue for multiple CAM clients; discovery grants no machine ownership and does not replace TCP session.auth. Shutdown stops broadcasts/releases UDP.

CAM implements this framing; server CLI configures discovery. Actual cross-device broadcasts still require deployment-interface, switch, and CAM integration testing.

## Frame format

Each frame has a fixed 24-byte header followed by the specified UTF-8 JSON byte count:

```text
CAM2 | SEND_GCODE padded with NUL to 16 bytes | 4-byte body length | JSON body
```

| Offset | Length | Content |
| --- | --- | --- |
| 0 | 4 | ASCII magic `CAM2`, external TCP protocol version 2 |
| 4 | 16 | ASCII type, right-padded NUL (0x00), no embedded NUL |
| 20 | 4 | Unsigned big-endian body byte count, excluding header |
| 24 | 1–65,536 | UTF-8 JSON with `version` equal to 2 |

| Header type | Meaning | Corresponding body |
| --- | --- | --- |
| `AUTH` | Connection authentication | `session.auth` |
| `PING` | Heartbeat | `ping` |
| `JOG_START` | Start continuous jog | `jog.start` |
| `JOG_KEEPALIVE` | Renew current held operation | `jog.keepalive` |
| `JOG_STOP` | Stop this jog | `jog.stop` |
| `SEND_GCODE` | Send machining file | `upload.begin`, `upload.chunk`, `upload.finish` |
| `ABORT_GCODE` | Cancel current reception | `upload.abort` |
| `GET_RECEIPT` | Query receipt | `upload.receipt` |
| `GET_STATUS` | Query machining state | `status.get` |
| `SUB_STATUS` | Subscribe to state | `status.subscribe` |
| `UNSUB_STATUS` | Unsubscribe | `status.unsubscribe` |
| `REPLY` | Successful response | requestId and result |
| `ERROR` | Failed response | requestId and error |
| `STATUS` | Unsolicited state | machine.status event with state or error |
| `REQUEST` | Unsupported method | Other method, returning unsupported_method |

Validate magic/type/length before reading body. Header type must match method; mismatch returns `message_type_mismatch` and closes. Upload begin/chunk/finish all use SEND_GCODE, distinguished by body method. Responses use the same header, distinguishing receipts, errors, and unsolicited state.

Handle TCP fragmentation/coalescing using header length. Wrong magic, unknown types, invalid lengths, duplicate JSON keys, non-finite numbers, extra envelope fields, or invalid versions cause error and close. Old external v1 four-byte-length-only frames are no longer accepted; update CAM senders. Internal Unix framing is unchanged.

Fixed request:

```json
{"version":2,"requestId":"unique-id","method":"ping","params":{}}
```

requestId is 1–64 characters, unique within the connection; replies echo it:

```json
{"version":2,"requestId":"unique-id","result":{"alive":true}}
```

Failures return error:{code,message} without result. If request ID cannot be recovered, use an empty ID. Business-parameter errors normally allow continuing; invalid chunks/failed commits abort current upload and clean unpublished files.

Pre-authentication timeout is 10 seconds; frame body reads/response writes also 10 seconds. Authenticated request-idle timeout defaults to 60 seconds, configurable by --idle-timeout. Subscription pushes do not renew it; CAM should ping every 30 seconds. Accept at most four connections and close extras. Each connection permits 100,000 distinct IDs before reconnecting.

## Authentication and methods

The first valid request after connection must be:

```json
{"version":2,"requestId":"auth-1","method":"session.auth","params":{"token":"<token>"}}
```

Success returns authenticated:true. Unauthenticated or invalid-token requests return unauthorized and close. After authentication:

| Method | Parameters | Result |
| --- | --- | --- |
| `ping` | Empty object | alive:true |
| `upload.begin` | transferId, filename, size, sha256 | state:"receiving", nextOffset:0 |
| `upload.chunk` | offset, Base64 data | nextOffset |
| `upload.finish` | Empty object | Complete receipt plus duplicate boolean |
| `upload.abort` | Empty object | aborted:true, clean incomplete upload |
| `upload.receipt` | transferId | Persistent published receipt |
| `status.get` | Empty object | Fresh machining state |
| `status.subscribe` | interval in seconds, 1–60 | subscribed:true, then pushes |
| `status.unsubscribe` | Empty object | subscribed:false, stop this connection's pushes |

One upload per connection may coexist with status queries/subscriptions. Requests execute serially in receive order; independent asynchronous pushes share a send lock with responses, preventing interleaved bytes. Clients distinguish requestId responses from event pushes; the next frame need not answer the last request. Resubscription replaces the old subscription.

## Program reception

CAM generates transferId as a lowercase hyphenated UUID and reuses it for retransmission. filename is a basename of ASCII letters/digits/underscore/hyphen/dot, starting alphanumeric, ending in lowercase `.ngc`, `.nc`, or `.gcode`, with at most 120 characters before the extension. Separators/URL encoding are invalid.

size is the positive complete-file byte count, default maximum 64 MiB, configurable by --max-bytes. sha256 is the full original file's 64-character lowercase hexadecimal digest. Files must be nonempty UTF-8 without NUL; LinuxCNC owns G-code semantics.

Sequence: upload.begin, chunks, finish. Offset starts at zero and must equal prior nextOffset. Each decoded chunk is at most 32,768 bytes and no larger than declared remaining bytes. UTF-8 characters may span chunks; decoding is incremental.

After complete reception/hash verification, sync program/receipt then atomically publish the directory. First success:

```json
{"version":2,"requestId":"finish-1","result":{"transferId":"550e8400-e29b-41d4-a716-446655440000","filename":"part.ngc","size":1234,"sha256":"<64-character-digest>","state":"received","duplicate":false}}
```

Resubmission with identical ID/name/size/hash returns the same receipt and duplicate:true. Content/name conflicts return transfer_id_conflict without overwriting. upload.receipt omits temporary duplicate. If receipt is lost, query first; unknown_transfer means no published receipt and permits full retransmission under the original ID.

Disconnect, request timeout, explicit abort, chunk/hash errors, and normal shutdown clean incomplete files. Power loss/forced termination may leave hidden `.receiving-*` directories, cleanable by administrators after shutdown; they are never published as complete. No cross-connection resume exists. Received programs remain until local manual cleanup; manage inbox capacity at deployment.

## Status feedback

Machine configuration follows the same read-only chain: CAM → Rust GET_STATUS/status.get → local Unix machine.status → Python StatusReader → LinuxCNC state/current-instance INI. Rust neither reads LinuxCNC directly nor adds a configuration channel. Optional configuration is forwarded unchanged with actual enabled axes, mm/degree soft limits, per-minute maximum velocity, and kinematics. See [local control protocol](local-control-protocol.md). Missing/unknown configuration displays unknown; do not retain stale machine configuration after disconnect. Axis count is not simultaneous machining capability.

After subscription acknowledgement, sample immediately and then every interval. Each sample uses a separate local Unix read-only machine.status connection without ownership, jogging renewal, error-channel consumption, or an existing desktop session requirement.

```json
{"version":2,"event":"machine.status","data":{"connected":true,"programState":"running","currentLine":12,"taskLine":100,"readLine":120,"progressPercent":null,"transferId":null}}
```

| Field | Meaning |
| --- | --- |
| `connected` | Valid LinuxCNC state |
| `programState` | idle, running, paused, busy, estop, off, unknown |
| `file` | Current local LinuxCNC program path |
| `transferId` | ID only when path is in current inbox and matches receipt filename; otherwise null |
| `currentLine` | LinuxCNC motion_line, motion execution line |
| `taskLine` | LinuxCNC current_line, task execution line |
| `readLine` | LinuxCNC read_line, interpreter lookahead |
| `progressPercent` | Currently null; never estimated from line number |
| `mode`, `powered`, `estop`, `paused` | Operating mode, power, emergency stop, pause |
| `queueDepth`, `activeQueueDepth` | Queue state |
| `tool`, `spindleSpeed`, `feedOverride`, `flood`, `mist` | Tool number, commanded spindle RPM, feed ratio, coolant |

With reachable controller but unavailable LinuxCNC, return connected:false, programState:"unknown", null lines/percentage, optionally omitting other fields. If controller is unreachable or no state arrives within two seconds, queries return controller_unavailable and subscriptions push an error without stale state:

```json
{"version":2,"event":"machine.status","error":{"code":"controller_unavailable","message":"local controller status unavailable"}}
```

Subscriptions continue sampling and resume actual feedback on recovery. Buffered events may precede unsubscribe acknowledgement; no new events follow it. Closing CAM cancels subscription without affecting machining.

transferId associates inbox files only by local path; copied/edited files are not new job records. received means complete reception; idle means currently idle. Neither proves machining success. Explicit automatic machining uses the lifecycle below. Percentages, remaining time, and remote pause/stop interfaces are outside this scope.

## Independent transfer, independent homing, and combined machining

On 2026-10-26, the user's latest requirement split capabilities: transfer.rs receives files, homing.rs requests independent homing, wf-transhoming.rs requests machining after homing. upload.finish no longer implicitly starts machining. Even with --auto-run, uploads/receipt queries neither call control nor move the machine. Legacy CAM clients must add explicit start requests instead of treating reception as machining start.

Configure controller --cam-inbox. Rust --auto-run now only permits explicit start requests; without it, reject starts but permit existing-job queries/cancellation. Upload remains begin → chunk → finish with size/SHA-256/UTF-8 checks and atomic publication; duplicate files return receipts only.

| External method | Header | Parameters | Result |
| --- | --- | --- | --- |
| `home.start` | `REQUEST` | `{operationId, clearanceConfirmed:true}` | `{job}`; home only, no program load |
| `home.status` / `home.cancel` | `REQUEST` | `{operationId}` | `{job}`; query/cancel specified homing |
| `workflow.start` | `REQUEST` | `{transferId, clearanceConfirmed:true, machiningConfirmed:true}` | `{job}`; validate received file → home all → load → machine |
| `workflow.status` / `workflow.cancel` | `REQUEST` | `{transferId}` | `{job}`; query/cancel combined task |
| `job.start` | `START_JOB` | `{transferId}` | `{job}`; machining on an already-homed machine, no auto-homing |
| `job.status` | `GET_JOB` | `{transferId}` | `{job}`; null without execution record |
| `job.cancel` | `REQUEST` | `{transferId}` | `{job}`; cancel specified execution |

operationId/transferId are lowercase UUIDs, distinct from connection-scoped requestId. Independent homing persists at private inbox `.homing/<operationId>.json` without placeholder G-code; program intent stays in transfer-directory execution.json. An ID never executes twice; a transfer cannot switch between machining-only and home-then-machine. Incomplete intents become unknown after restart, without scanning/resuming.

Authentication is unchanged. Local v2 methods are cam.home.start/status/cancel, cam.workflow.start, and cam.job.start/status/cancel; workflow.status/cancel reuse local job methods. One Controller on one worker performs all native calls. Rust does not read HAL, send MDI, start/stop the core, or clear emergency stop/enable automatically.

Combined requests validate received files, copy to read-only `.execution.ngc`, and persist intent. Following acknowledgements, switch to manual/joint, clear and confirm old homing flags, then HOME ALL. Load only after all joints are homed, none is homing, interpreter/motion queues are idle, and in-position is true. Confirm correct file/AUTO mode, then send AUTO_RUN(0) once. Explicit combined workflows rehome even if previously homed; use job.start to reuse current homing.

Homing requires connected, enabled, not emergency-stopped, idle, stopped spindle, no limit override, and valid homing configuration for all joints. Machining additionally requires all joints homed, no hard limits/override, and block delete off. clearanceConfirmed means the operator confirms the entire homing path clear with current tool/workpiece/fixtures; this machine homes Z downward, so an earlier empty-table/tool-free test is insufficient. machiningConfirmed means work coordinates, compensation, and clamping are ready; homing does not set these parameters automatically.

States: accepted, homing, loading, starting, running, completed, error, unknown. Independent homing completed confirms homing only. Combined completion requires AUTO_RUN NML serial RCS_DONE and finished motion. Active homing waits at most 300 seconds; timeout cancels subsequent steps and reports unknown without claiming physical axes stopped. Cancel sends one abort to the specified active task, returns unknown, and requires observing actual state; requested cancellation is not completed stopping. Missing/finished IDs do not stop unrelated motion.

Errors, emergency stop, power loss, lost state, external writers, cancellation, and service exit prevent unsent machining steps. Never retry unknown outcomes. CAM/desktop disconnect does not revoke service-accepted tasks; service shutdown stops further submissions. Reject new work when busy rather than queueing for future enable/idle. Lost responses are resolved only by home.status/workflow.status/job.status.

## Continuous XYZ jogging

An authenticated TCP connection may send the following. Each held gesture uses a fresh lowercase jogId UUID; never retry/replay jog.start. `{jogId,accepted:true}` means control acceptance, not physical target attainment.

| Method | Parameters |
| --- | --- |
| `jog.start` | jogId, axis X/Y/Z, integer direction ±1, feedRate in mm/min with 0 < value ≤ 3000 |
| `jog.keepalive` | Same jogId; renew only, never restart |
| `jog.stop` | Same jogId; close this operation's control session |

manual uses public Unix cam.jog.start/keepalive/stop and the existing Controller alongside Qt. Return control_in_use when another jog runs; never preempt motion. Accept only connected XYZ axes actually in world mode, without guessing joint mappings. Convert mm velocity using fresh linearUnits to native units/second with increment=0. Controller checks fresh homing, enable, emergency stop, busy state, and INI velocity limits without automatic homing, power-on, or program execution.

CAM renews about every 150 ms while held. Rust forwards keepalive only after a new request on that connection, never in the background. After 450 ms without renewal, TCP disconnect, explicit stop, or shutdown, close this operation's Unix connection to revoke unsent steps/stop its jogging. The controller has a separate 600 ms lease. Late renewal cannot restore expired jogging; release and press again. Software leases are not hard real-time stop guarantees: native LinuxCNC/NML calls and scheduling can delay handling. Network leases never replace physical safety chains.

Browser key release, pointercancel, capture loss, focus loss, page hiding/exiting, and component unmount revoke the operation. Old machine services return unsupported_method and must be updated; never bypass with MDI/G-code.

CAM jogging uses the service's same Controller without attaching/preempting desktop ownership. Disconnect closes the corresponding Unix connection and revokes its lease; desktop status remains available and emergency stop/stop take priority. Independent 450 ms network and 600 ms service leases are unchanged.
