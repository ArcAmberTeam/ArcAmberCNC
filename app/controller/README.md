# Local Python controller service

Read [AGENTS.md](AGENTS.md), [service responsibilities](src/betterlinuxcnc_service/AGENTS.md), and the [public control protocol](../../docs/local-control-protocol.md) before implementation. This document and all Markdown follow root [AGENT.md](../../AGENT.md): no autonomous changes or unsolicited proposals; an explicit human request and second confirmation are required. Use English and do not add change records, operational logs, email addresses, or key material.

## Responsibilities and entry points

The service provides public v2 Unix socket status, control sessions, commands, CAM requests, and isolated interpreter preview. Legacy v1 `health` remains diagnostic compatibility only; its response is not evidence of machine connectivity.

- `betterlinuxcnc_service.main` and `serve`, `python -m betterlinuxcnc_service`, and installed `betterlinuxcnc-service` expose the service.
- `bettercnc_controller.Controller` owns operation policy, validated machine writes, and the single command/error channels. `StatusReader` supplies read-only snapshots on the same serialized worker.
- `bettercnc_preview.parse_program` and its CLI adapt the native `gcode` extension in a separate process.

The desktop and Rust CAM service use the documented socket protocol, never private implementation imports. The service does not start LinuxCNC or run the real-time servo loop. Unattached `machine.status` reads state without taking control or renewing jogging leases. Lost responses remain unknown; reconnect never replays motion.

## Installation and verification

The package declares Python 3.11+ and no third-party Python runtime dependencies. Actual control and preview require the installed native LinuxCNC interfaces. Package installation, startup, and readiness do not establish physical motion acceptance.

Build wheels and run Ruff, public-API tests, socket tests, and real file-only interpreter regressions only in GitHub CI. Local and target source builds/tests are prohibited. Install completed published packages on the target through the project update flow; use [local connection instructions](../../docs/linuxcnc-local-connection.md) for explicitly authorized runtime operations.

Extend an existing owner for related behavior. Add a new file or directory only when a distinct responsibility requires isolation, and verify existing public APIs before introducing dependencies.
