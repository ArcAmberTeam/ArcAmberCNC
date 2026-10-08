# Rust 本地通信边界

先遵循根目录 [AGENT.md](../AGENT.md) 和 `$code-boundary-standards`。

- 本目录是独立 Rust 库，只拥有 Unix domain socket 的 v1 本地诊断通信；不依赖 Tauri、Web、Qt、HAL 或驱动，不启动 Python 或 LinuxCNC。
- `src/lib.rs` 是唯一公开入口，只公开 `probe_service` 与 `ServiceHealth`；`service` 模块是私有实现。宿主通过公开 API 提供 socket 路径，不通过深层导入访问实现。
- v1 协议仅有 `health`：四字节大端长度加 UTF-8 JSON、最大 65536 字节、总超时两秒。只接受诊断模式且 `machine_connected: false` 的响应；该结果不能判断真实机床连接状态。
- `python.service/` 已提供独立的 v2 控制会话和预览；本库保留 v1 兼容性，不发送 v2 机床动作、不复制 Python 服务的机床规则、不承担实时职责。Qt 的现有 Python 会话适配层独立连接 v2 服务，不依赖本库。
- 集成测试通过公开库 API、Python CLI 与 Unix socket 验证协议，不导入私有 Python 实现，不启动模拟器、实时线程或硬件。
- 按通信能力划分后续私有实现；只有出现真实平台差异才增加架构或平台子目录，不建立没有实现的驱动、HAL 或 CPU 架构占位。
- 工具链固定为 `rust-toolchain.toml`，依赖固定为 `Cargo.lock`。在本目录运行 `cargo fmt --check`、`cargo check --locked --all-targets`、`cargo clippy --locked --all-targets -- -D warnings` 和 `cargo test --locked`。集成测试需要 Python 3.11+，可通过 `SERVICE_TEST_PYTHON` 指定解释器。
- README 仅人工维护，不自动新增或改写。
