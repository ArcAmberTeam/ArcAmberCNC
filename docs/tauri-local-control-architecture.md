# Tauri local control architecture record

2026-10-08: this is a historical architecture record. Web/Tauri and deployment scripts were removed; v1 diagnostics moved to `tools/diagnostics/`. The official UI is `app/desktop/`, using PySide6/Python v2 sockets with the existing controller. See [local control protocol](local-control-protocol.md) and [Qt migration notes](qt-qml-migration.md). Tauri/Web directories, CI, and design conventions below are not current entry points.

Original decision: 2026-09-22. It specified Tauri-only product operation on Debian 13 / Intel integrated graphics.

On 2026-10-02, the user decided to migrate to native Qt Quick/QML, adding official desktop entry `qt/`. See [Qt migration notes](qt-qml-migration.md) for current decisions/checks. `frontend/` remained for migration comparison/Web preview, retaining Tauri/Rust and diagnostics tests. This document records existing implementation/prior plans without requiring Qt to use Vue, Tauri IPC, or Rust. Future Qt would use an independent C++ adapter to the existing Unix socket/Python boundary; at that stage it was presentation-only without machine integration.

The Tauri desktop environment and local Python diagnostics service had been established, with `health` through Rust/Unix sockets. The UI distinguished reachable service from unconnected machine. Only that diagnostic chain was implemented; motion, state Channels, persistent sessions, control ownership, and failure-stop policy below remained future requirements. Diagnostics used short connections; the service started explicitly without automatically starting LinuxCNC. See [Python service instructions](../app/controller/README.md).

## Original Tauri control chain

```text
Vue feature UI
    │ Public control-session interface
    ▼
Tauri IPC: commands / state Channel
    ▼
Rust desktop environment and communication bridge
    │ Unix domain socket (same computer)
    ▼
Python controller service
    │ LinuxCNC Python interface
    ▼
LinuxCNC control core, real-time motion, and HAL
```

The prohibition on HTTP/WebSocket control services and browser device adapters continues through Qt migration; FastAPI/OpenAPI are unnecessary. Browsers serve UI previews, design material, and presentation tests only; Vite development serving is not a machine interface. Tauri/Rust/Channel responsibilities below describe the retained Tauri path only; command lifecycle, single writer, and fresh-state constraints also apply to future Qt integration.

## Layer responsibilities

| Layer | Responsibility | Public boundary |
| --- | --- | --- |
| Vue features | Presentation, input, operation flow | Submit operations/read state through `controller-session` |
| `controller-session` | Sessions, freshness, command lifecycle | Explicit home/jog/run operations; private Tauri adapter |
| `protocol` | Structures, versions, validation | Small explicit data contracts, no UI/device implementation |
| `desktop-platform` | Windows, file dialogs, generic desktop facilities | No machine session or duplicate control connection |
| Rust | Tauri permissions, command allowlist, socket forwarding, subscriptions | Explicit Tauri commands/state channels, no arbitrary socket paths/Python calls exposed to Web |
| Python | Device identity, ownership, machine preconditions, scheduling, state, errors | Local protocol; application's sole LinuxCNC command writer/error reader |
| LinuxCNC | Interpolation, motion planning, real-time threads, hardware | Existing official interfaces; no real-time control in UI processes |

Rust validates desktop/communication boundaries; Python owns machine rules. Disabled UI buttons cannot replace Python prechecks. Vue components must not call Tauri, sockets, or LinuxCNC directly. Update dependency checks when modules are added; do not create empty prototype packages.

## Messages and state

- Web submits Tauri commands to Rust; Rust streams state through Channels. Channels do not replace rate limits, queue bounds, or state coalescing.
- Rust/Python use persistent Unix streams with length-bounded JSON initially. Specify encoding, maximum messages/queues, invalid-message behavior, and versions. One read/write is not necessarily one complete message.
- Requests carry request ID, session ID, action, and parameters. Distinguish accepted/completed/rejected/unknown. Timeout does not mean unexecuted; reconnect never replays motion, spindle, or MDI.
- State carries service-instance identity, increasing sequence, and collection health. Synchronize full state before enabling actions. Expired state is not operable even with an open socket.
- Continuous coordinates may coalesce old snapshots; alarms/results need inspectable ordering and gap handling, never silent dropping.
- Preview geometry, large transfers, and interpretation stay separate from command queues. Determine chunk sizes/update rates by target measurement.
- Maintain TypeScript/Rust/Python types/validators from unified message definitions, choosing generation tools during implementation. Generated types do not replace runtime validation.

## Local permissions and lifecycle

Unix sockets are local, not inherently exclusive to this application. Restrict directory/file permissions, check peer identity, and validate sessions. One machine grants one application control session write access at a time; multiple windows coordinate through that session instead of independent Python connections.

Python must identify the LinuxCNC instance/configuration explicitly; socket existence alone does not establish the correct device. Coordinate write access from other tools/HAL during integration.

Handle window close, webpage focus loss, Rust crash, Python restart, and LinuxCNC exit separately. Continuous-jog permission/timeout stopping must not depend solely on a webpage release message; cover a frozen page with live Rust. Define/verify session invalidation, stale-state, and shutdown-stop policies before production integration. Killing UI/Python is not proof the machine stopped. Physical emergency stop remains a hardware safety circuit.

## Delivery and subsequent acceptance

At this stage CI included Web preview, Python package validation, Debian 13 Tauri `.deb` builds, and Rust→Python diagnostic integration. Python/desktop packages uploaded independently without automatic machine installation. Controller supervision, target graphics, and real LinuxCNC integration remained pending; tests did not establish device connectivity.

Control integration must at least verify normal commands/results, version mismatch, invalid arguments, rejection of a second owner, disconnect/reconnect, stopped state collection, command timeout, focus loss/exit, and stop requests under large-data load. Measure latency on target; Unix sockets do not guarantee real time.

## Official interface references

- [Calling Rust from Tauri frontend](https://v2.tauri.app/develop/calling-rust/): commands, arguments, results, asynchronous calls.
- [Sending data to Tauri frontend](https://v2.tauri.app/develop/calling-frontend/): Channels/events.
- [Rust UnixStream](https://doc.rust-lang.org/std/os/unix/net/struct.UnixStream.html): Unix streams.
- [LinuxCNC Python interface](https://linuxcnc.org/docs/2.9/html/config/python-interface.html): command/status/error channels.

Interface capabilities come from official documentation; module ownership, protocol choices, and acceptance scope are project architecture decisions.
