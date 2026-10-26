# Python service responsibilities

Follow the local [AGENTS.md](AGENTS.md), [controller guide](../../AGENTS.md), and root [AGENT.md](../../../../AGENT.md). Markdown is protected: no autonomous edits or unsolicited proposals; only an explicit human request followed by second confirmation permits changes. Keep prose English and exclude change records, logs, email addresses, and key material.

| File | Responsibility |
| --- | --- |
| `__init__.py` | Public `main` and `serve` exports. |
| `__main__.py` | Package CLI entry point. |
| `_server.py` | Unix socket lifecycle, connections, sessions, and service composition. |
| `_protocol.py` | Wire framing and protocol validation. |
| `_controller_runtime.py` | Serialized dispatch to public Controller and StatusReader APIs. |
| `_preview_jobs.py` | Isolated preview job lifecycle. |
| `_wire_snapshot.py` | Public snapshot serialization. |

Underscore-prefixed files are private. Callers and external tests use package exports, installed CLI, and the [public protocol](../../../../docs/local-control-protocol.md). v2 supplies real status/control and preview; v1 health retains diagnostic compatibility. Service reachability and machine connectivity remain distinct.

Keep transport/session orchestration here, machine operation rules in `bettercnc_controller`, and file interpretation in `bettercnc_preview`. Neither downstream package depends back on transport. Do not duplicate interlocks in protocol handlers, block the worker on preview interpretation, or add a second native command/error-channel owner.

Verification uses public interfaces and controlled external dependencies in GitHub CI only; do not start machines or simulators. See [controller overview](../../README.md).
