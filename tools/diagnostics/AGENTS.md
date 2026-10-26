# Rust local communication boundaries

First follow the root [AGENT.md](../../AGENT.md).

- This is an independent Rust library owning only v1 local diagnostics over Unix domain sockets. It does not depend on Tauri, Web, Qt, HAL, or drivers, and does not start Python or LinuxCNC.
- `src/lib.rs` is the sole public entry point, exposing only `probe_service` and `ServiceHealth`; `service` is private. Hosts supply socket paths through the public API, not deep implementation imports.
- v1 supports only `health`: four-byte big-endian length plus UTF-8 JSON, maximum 65536 bytes and a two-second overall timeout. Accept only diagnostic-mode responses with `machine_connected: false`; this does not establish actual machine connectivity.
- `app/controller/` provides independent v2 control sessions and previews. This library retains v1 compatibility without sending v2 machine actions, duplicating Python machine rules, or performing real-time work. Qt's Python session adapter independently connects to v2 without this library.
- Integration tests verify the protocol through public library APIs, Python CLI, and Unix sockets, not private Python imports, simulators, real-time threads, or hardware.
- Organize future private implementation by communication capability. Add architecture/platform directories only for actual differences; do not create unimplemented driver, HAL, or CPU placeholders.
- Pin the toolchain with `rust-toolchain.toml` and dependencies with `Cargo.lock`. In this directory, run `cargo fmt --check`, `cargo check --locked --all-targets`, `cargo clippy --locked --all-targets -- -D warnings`, and `cargo test --locked`. Integration tests require Python 3.11+, selectable with `SERVICE_TEST_PYTHON`.
- README files are maintained manually; do not automatically add or rewrite them.
