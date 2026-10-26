# Python service internal responsibilities

[Service startup and protocol](../../README.md) · [Project module map](../../../../docs/module-map.md)

## Role and language

Python 3.11+, standard library only. Currently queries local service health without importing LinuxCNC, reading hardware, or sending motion commands.

## Files and entry points

| File | Responsibility |
| --- | --- |
| `__init__.py` | Public package entry point exporting `main` |
| `__main__.py` | Entry point for `python -m betterlinuxcnc_service` |
| `_server.py` | Socket paths, permissions, listening, framing, timeouts, connection limits, and process-exit cleanup |
| `_protocol.py` | JSON parsing, field/version validation, method selection, and result/error envelopes |

Underscore-prefixed files are private. Callers use CLI and socket protocol rather than importing these files; tests likewise observe the installed package through CLI and communication endpoints.

## Upstream, downstream, and boundaries

Upstream is the Rust desktop environment; no downstream LinuxCNC connection exists yet. `health` always returns diagnostic mode and `machine_connected: false`; no other methods are accepted.

Transport handlers own connections/messages; protocol parsers own the message contract. Future control additions must define separate machine-access and operation-rule owners rather than placing run, home, and jog logic directly in `_server.py`.

Local socket permissions restrict users but cannot prove a client is Tauri. Persistent sessions, control ownership, and stop-on-disconnect remain unimplemented. Python does not run the real-time servo loop; preview interpretation must not block the controller service.

See the parent service document for Ruff, package-build, and installed unittest commands; protocol changes also require Rust cross-process integration tests.
