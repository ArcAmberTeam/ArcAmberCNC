# Rust 系统服务边界

遵循根目录 `AGENT.md`。README 由人工维护。

- `src/lib.rs` 的 `run` 和已安装二进制 `betterlinuxcnc-cam-link` 是公开入口。`cam_link` 内部实现私有；本模块只拥有 CAM 联动；其他应用按职责建立同级模块，不放入诊断库或 Python 包。
- CAM Link 拥有 TCP 6522、可选 UDP 8421 发现、独立收件目录、状态订阅和网络连接生命周期。它不加载 Python、不创建 LinuxCNC/NML/HAL 通道、不启动或保活其他进程。启动顺序及进程保活属于 `app/launcher`。
- `protocol` 拥有 CAM2 帧及严格 JSON；`inbox` 拥有文件校验和原子发布；`control` 仅适配公开 v2 Unix 协议；`manual` 通过 control 管理点动租约；`feedback` 通过 control 读取状态并用 inbox 关联文件；`discovery` 拥有有界 UDP 握手；`transfer` 只接收文件，`homing` 提交独立回零，`wf-transhoming.rs` 提交组合流程；`session` 分发各能力。禁止反向依赖和公开内部类型来迁就测试。
- 默认空参数 `session.auth` 一键直连。令牌/TLS 仅在显式配置时启用，不能因认证失败自动降级。UDP 不传令牌、文件或加工状态，发现握手不授予控制权。
- 上传和回执始终只涉及文件，即使启用 `--auto-run` 也不触发运动。该选项仅允许显式 `home.start`、`job.start`、`workflow.start`；回零路径确认和组合加工准备确认必须由调用方明确提供。`workflow` 的回零→加工序列、取消和持久化均由 Controller 拥有，Rust 不轮询拼接运动。状态与取消不受网络启动开关限制；丢失响应为 unknown，重启不扫描补跑，禁止自动重试。
- XYZ 点动通过同一连接的 `cam.jog.start/keepalive/stop`。450 ms 的网络租约独立于控制服务 600 ms 租约；到期、断开、停止及服务退出必须关闭对应 Unix 连接，不能后台自行续租或抢占桌面。
- 磁盘上传操作在阻塞任务池执行，不能阻塞点动计时。未完成目录仅由 Upload 生命周期清理，已发布文件不得覆盖。
- 测试通过真实 Rust CLI、TCP/UDP/Unix socket 和 Python 服务公开入口。vendor 替身来自测试目录；不得启动机床或模拟器。Python 仅作为测试客户端及现有本地控制服务，不实现 CAM 网络服务。
- 在此目录运行 `cargo fmt --check`、`cargo check --locked --all-targets`、`cargo clippy --locked --all-targets -- -D warnings`、`cargo test --locked`；跨进程测试需要 Python 3.11+（`SERVICE_TEST_PYTHON`）。测试 Python 使用 `app/controller/pyproject.toml` 的 Ruff 规则。
