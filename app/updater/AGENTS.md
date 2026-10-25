# Rust Release 更新服务

遵循根目录 `AGENT.md`。`src/lib.rs::run` 和 `betterlinuxcnc-updater` CLI 为公开入口，`updater` 内部实现私有。模块不依赖 CAM、Qt、Python 实现、HAL 或 LinuxCNC 扩展。

- Rust 拥有当前仓库最新正式 Release 的 HTTPS 查询、按架构下载、SHA-256 校验、Debian 包信息核对、缓存和安装记录。Qt 只通过 JSON 行 CLI 观察状态、请求下载及安装。
- 下载与安装分离。安装前重验摘要、包名、版本和架构；拒绝版本回退。只有应用更新包，不写入控制器固件、INI/HAL、机床参数或仓库工作区。
- 安装由独立 systemd 用户单元执行，正常停止已有启动器后再次确认控制端点和原生锁消失；状态未知、暂停、运动、排队任务、主轴运转或使能状态下拒绝安装。只读 `machine.status` 不附着控制会话、不发送机床命令。
- 需要管理员权限时通过系统 pkexec 授权调用固定 apt-get 路径，不存储密码。安装失败不报告成功，不启动可能处于混合版本状态的控制系统。安装完成核验版本后才重新启动原有受管启动器。
- 测试使用临时目录、发布元数据和受控网络/进程接口；不访问真实机床、不执行真实安装、不发布 Release。真实 StatusReader/Unix 协议测试只在外部注入 vendor 接口，可用 SERVICE_TEST_PYTHON 指定 Python 3.11+。运行 cargo fmt --check、cargo check --locked --all-targets、cargo clippy --locked --all-targets -- -D warnings、cargo test --locked。
- README 只由人工维护。
