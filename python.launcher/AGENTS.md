# Python 启动编排边界

遵循根目录 `AGENT.md` 和用户指定的 `code-boundary-standards`。

- `bettercnc_launcher` 的 `main`、`python -m bettercnc_launcher` 和 `betterlinuxcnc-launch` 是公开入口。下划线文件私有，运行时仅依赖 Python 标准库。
- 启动器拥有配置校验、单实例锁、子进程、日志、启动顺序和就绪探测；只通过已安装 CLI 和只读公开 Unix 协议协作，不导入 Qt、LinuxCNC、服务或控制器实现，不获取控制会话，不发送机床命令。
- 原生 `linuxcnc <ini>` 继续拥有实时核心、HAL、DISPLAY 和底层清理。启动器不改写 INI/HAL，不接管已有服务。默认保活只重启已退出的模块，不重放命令；核心重启必须先确认原进程组和原生锁均已释放。
- 安装产物提供 XDG 会话自动启动项与 systemd 用户服务，不启动 root GUI；主进程 SIGINT/SIGTERM/SIGKILL 不触发 systemd 重启。退出 78 表示需人工处理的运行状态，禁止通过 systemd 循环抢占其他实例。
- 控制服务先就绪，LinuxCNC 状态连接后才开启 CAM。核心已启动后的异常必须保留核心/控制服务供本地操作员处理；停止信号只在新鲜状态明确空闲时请求原生清理，不强杀核心进程组。
- 测试从公开 CLI、真实进程及 Unix socket 观察行为，使用可执行程序替身，不运行 LinuxCNC、模拟器、实时线程或硬件。构建安装 wheel 后测试；同时验证依赖边界和桌面安装入口。README 只由人工维护。
