# Python 启动编排边界

遵循根目录 [AGENT.md](../../AGENT.md)。本仓库永久停用 `$code-boundary-standards`，不将其作为开发、测试或审查前置要求。

- `bettercnc_launcher` 的 `main`、`python -m bettercnc_launcher` 和 `betterlinuxcnc-launch` 是公开入口。下划线文件私有，运行时仅依赖 Python 标准库。
- 启动器拥有配置校验、单实例锁、子进程、日志、启动顺序和就绪探测；只通过已安装 CLI 和只读公开 Unix 协议协作，不导入 Qt、LinuxCNC、服务或控制器实现，不获取控制会话，不发送机床命令。
- 原生 `linuxcnc <ini>` 继续拥有实时核心、HAL、DISPLAY 和底层清理。启动器不改写 INI/HAL，不接管已有服务。默认保活只重启已退出的模块，不重放命令；核心重启必须先确认原进程组和原生锁均已释放。
- 安装产物提供 XDG 自动启动项、专用 X11 会话与 systemd 用户服务，不启动 root GUI。`--kiosk-session` 持续维持专用会话，通过已安装桌面 CLI 显示不连接机床的启动状态页；启动器失败时不退回普通桌面。主进程 SIGINT/SIGTERM/SIGKILL 不触发 systemd 重启。退出 78 表示需人工处理的运行状态，禁止通过 systemd 循环抢占其他实例。
- 控制服务先就绪，LinuxCNC 状态连接后才开启 CAM。核心已启动后的异常必须保留核心/控制服务供本地操作员处理；停止信号只在新鲜状态明确空闲时请求原生清理，不强杀核心进程组。
- 测试从公开 CLI、真实进程及 Unix socket 观察行为，使用可执行程序替身，不运行 LinuxCNC、模拟器、实时线程或硬件。构建安装 wheel 后测试；同时验证依赖边界和桌面安装入口。当前用户禁止本地及目标机构建、源码测试，包括本地 Docker；这些验证只由 GitHub CI 执行，目标机仅安装完成的 DEB。README 只由人工维护。

## 专用机启动与历史迁移

- 目标机部署已获用户授权；源码仍在本地修改并通过 Git 同步。具体环境和命令遵循 [本机连接说明](../../docs/linuxcnc-local-connection.md)，不要另建并行启动脚本或改写机床配置。
- 应用 `26.10.26.1` 使用 `/usr` 安装前缀，CMake 的 `BETTERCNC_PROJECT_DIR` 默认并在正式发布时固定为 `/etc/betterlinuxcnc`。用户服务读取其中的 `launcher.json`；旧 `/home/teto/ArcAmberCNC/launcher.json` 仅作为显式迁移的输入，安装包不覆盖真实配置。`--check` 只验证配置和依赖，不证明机床已连接。
- DEB 的固定 postinst 通过 `betterlinuxcnc-appliance provision` 幂等准备账户与目录；`prepare` 显式导入机床配置，`activate` 显式配置专用登录，后两者不由安装包或启动器自动执行。LightDM 以 `linuxcnc` 运行 `betterlinuxcnc-kiosk` X11 会话，由它导入实际 DISPLAY/Xauthority 并启动 `betterlinuxcnc-launcher.service`。不要复用旧账户的 UID/Xauthority，也不要同时手动启动另一套 launcher。服务 active 之后仍须检查日志、私有 `state.json` 的 ready、公开机床状态及 GUI 窗口。
- 操作账户 HOME 为 `/var/lib/betterlinuxcnc/home`，缓存为 `/var/cache/betterlinuxcnc/user`；父目录保持 root 所有。systemd 模式日志位于 `/var/log/betterlinuxcnc/launcher/<本次启动目录>/`。`BETTERCNC_SHARE_LOGS=1` 仅放宽日志目录和日志文件供维护组读取，state、socket 和锁仍私有。直接 CLI 启动默认写入配置所在目录的 `.runtime/launcher/`。按最新启动目录读 controller、linuxcnc、cam-link 日志，不硬编码旧 PID 或日志目录。
- `cnc-maint` 只通过固定 SSH 命令读取诊断，不拥有任意 shell、启动/停止服务或 sudo 权限。需要变更登录策略时按本机连接说明保留既有 root 维护会话；不通过启动器新增提权通道。
- 保留已有 CAM 配置。当前目标机启用了 `auto_run`，不能为连接验证随意上传测试程序或改变自动运行设置。启动成功不代表 CAM 收件加工或机床运动已验收。
