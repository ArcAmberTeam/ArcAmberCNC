# Python 启动编排边界

遵循根目录 [AGENT.md](../../AGENT.md)。本仓库永久停用 `$code-boundary-standards`，不将其作为开发、测试或审查前置要求。

- `bettercnc_launcher` 的 `main`、`python -m bettercnc_launcher` 和 `betterlinuxcnc-launch` 是公开入口。下划线文件私有，运行时仅依赖 Python 标准库。
- 启动器拥有配置校验、单实例锁、子进程、日志、启动顺序和就绪探测；只通过已安装 CLI 和只读公开 Unix 协议协作，不导入 Qt、LinuxCNC、服务或控制器实现，不获取控制会话，不发送机床命令。
- 原生 `linuxcnc <ini>` 继续拥有实时核心、HAL、DISPLAY 和底层清理。启动器不改写 INI/HAL，不接管已有服务。默认保活只重启已退出的模块，不重放命令；核心重启必须先确认原进程组和原生锁均已释放。
- 安装产物提供 XDG 会话自动启动项与 systemd 用户服务，不启动 root GUI；主进程 SIGINT/SIGTERM/SIGKILL 不触发 systemd 重启。退出 78 表示需人工处理的运行状态，禁止通过 systemd 循环抢占其他实例。
- 控制服务先就绪，LinuxCNC 状态连接后才开启 CAM。核心已启动后的异常必须保留核心/控制服务供本地操作员处理；停止信号只在新鲜状态明确空闲时请求原生清理，不强杀核心进程组。
- 测试从公开 CLI、真实进程及 Unix socket 观察行为，使用可执行程序替身，不运行 LinuxCNC、模拟器、实时线程或硬件。构建安装 wheel 后测试；同时验证依赖边界和桌面安装入口。README 只由人工维护。

## 已验证的目标机启动方式

- 目标机部署已获用户授权；源码仍在本地修改并通过 Git 同步。具体环境和命令遵循 [本机连接说明](../../docs/linuxcnc-local-connection.md)，不要另建并行启动脚本或改写机床配置。
- CMake 的 `BETTERCNC_PROJECT_DIR` 设为 `/home/teto/ArcAmberCNC`，使安装后的用户服务读取该项目的 `launcher.json`；不能误用默认 `/opt/arcambercnc`。`--check` 只验证配置和依赖，不证明机床已连接。
- SSH 启动时先确认 `DISPLAY=:0` 与 Xauthority，再导入 systemd 用户环境并启动 `betterlinuxcnc-launcher.service`；不要同时手动启动另一套 launcher。服务 active 之后仍须检查日志、`state.json` 的 ready、公开机床状态及 GUI 窗口。
- systemd 模式日志位于 `~/.local/state/betterlinuxcnc/launcher/<本次启动目录>/`；直接 CLI 启动默认写入配置所在目录的 `.runtime/launcher/`。按最新启动目录读 controller、linuxcnc、cam-link 日志，不硬编码旧 PID 或日志目录。
- 保留已有 CAM 配置。当前目标机启用了 `auto_run`，不能为连接验证随意上传测试程序或改变自动运行设置。启动成功不代表 CAM 收件加工或机床运动已验收。
