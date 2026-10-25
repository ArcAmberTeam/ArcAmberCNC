# Rust 系统服务边界

遵循根目录 `AGENT.md`。README 由人工维护。

- `src/lib.rs` 的 `run` 和已安装二进制 `betterlinuxcnc-cam-link` 是公开入口。`cam_link` 内部实现私有；本模块只拥有 CAM 联动；其他应用按职责建立同级模块，不放入诊断库或 Python 包。
- CAM Link 拥有 TCP 6522、可选 UDP 8421 发现、独立收件目录、状态订阅和网络连接生命周期。它不加载 Python、不创建 LinuxCNC/NML/HAL 通道、不启动或保活其他进程。启动顺序及进程保活属于 `app/launcher`。
- `protocol` 拥有 CAM2 帧及严格 JSON；`inbox` 拥有文件校验和原子发布；`control` 仅适配公开 v2 Unix 协议；`manual` 通过 control 管理点动租约；`feedback` 通过 control 读取状态并用 inbox 关联文件；`discovery` 拥有有界 UDP 握手；`session` 组合各能力。禁止反向依赖和公开内部类型来迁就测试。
- 默认空参数 `session.auth` 一键直连。令牌/TLS 仅在显式配置时启用，不能因认证失败自动降级。UDP 不传令牌、文件或加工状态，发现握手不授予控制权。
- 自动加工只在 `--auto-run` 下将新文件提交一次 `cam.job.start`。重复上传仅查询，重启不扫描补跑；丢失响应为 unknown，禁止自动重试。Controller 保持唯一命令/错误通道、机床联锁、接收回执校验及执行持久化。
- XYZ 点动通过同一连接的 `cam.jog.start/keepalive/stop`。450 ms 的网络租约独立于控制服务 600 ms 租约；到期、断开、停止及服务退出必须关闭对应 Unix 连接，不能后台自行续租或抢占桌面。
- 磁盘上传操作在阻塞任务池执行，不能阻塞点动计时。未完成目录仅由 Upload 生命周期清理，已发布文件不得覆盖。
- 测试通过真实 Rust CLI、TCP/UDP/Unix socket 和 Python 服务公开入口。vendor 替身来自测试目录；不得启动机床或模拟器。Python 仅作为测试客户端及现有本地控制服务，不实现 CAM 网络服务。
- 在此目录运行 `cargo fmt --check`、`cargo check --locked --all-targets`、`cargo clippy --locked --all-targets -- -D warnings`、`cargo test --locked`；跨进程测试需要 Python 3.11+（`SERVICE_TEST_PYTHON`）。测试 Python 使用 `app/controller/pyproject.toml` 的 Ruff 规则。
