# Python 本地服务边界

先遵循根目录 `AGENT.md`。

- 本目录是独立 Python 包；不导入前端实现，也不依赖原生 AXIS。
- v1 `health` 保持历史诊断格式；v2 提供单写入者控制会话、状态、命令和隔离预览。`machine.status` 允许未附着的本地观察者读取新鲜状态，不获取控制权或续租点动。不得伪造反馈，也不启动 LinuxCNC。
- 公开入口为 `betterlinuxcnc_service`（`main`、`serve` 与 `python -m betterlinuxcnc_service`）、`bettercnc_controller.Controller`（包括 `start_received`/`received_status` 的受限 CAM 作业接口）、`bettercnc_controller.StatusReader`、`bettercnc_preview.parse_program` 与预览 CLI；下划线文件为私有实现。
- service 只依赖 controller/preview 的公开入口。controller 拥有机床规则、文件写入和 LinuxCNC 命令/错误通道；preview 在独立进程调用 LinuxCNC 的 `gcode` 扩展，不复制解释器。两者不能反向依赖传输层或 Qt。
- 所有 Controller 调用在一个工作线程串行执行。CAM 作业归服务所有，可复用桌面当前 Controller；上传连接或桌面连接关闭不会撤销已接受的 CAM 作业，服务关闭/状态丢失则取消未发送步骤并记录 unknown，不中止已经运行的程序、不自动重放。点动必须有会话租约，失联停止本会话点动并取消未发送步骤，任何未知结果都不得自动重试。机床文件写入必须在最新状态校验后执行，不能信任客户端 capability。
- `StatusReader` 只拥有 `linuxcnc.stat`，与 Controller 在服务工作线程串行调用；不得创建命令或错误通道。CAM 网络服务已迁至 `../cam-link/`，本包不再提供 `bettercnc_cam_link` 或 Python 网络启动入口。
- Rust 服务通过公开 Unix 协议调用 `machine.status`、`cam.job.start/status`、`cam.jog.start/keepalive/stop`。控制服务仍拥有单一 Controller、联锁、持久化作业状态和独立点动租约，不依赖 Rust 私有实现。协议见 `../../docs/cam-link-protocol.md`。
- 测试从公开对象、安装后的 CLI 和 socket 观察行为；允许注入 vendor 模块、时钟和预览进程工厂，不导入私有文件。真实 gcode 测试仅解释临时程序，不启动模拟器或硬件。
- 连接检查使用未附着的 `machine.status`，不能为了诊断获取现有 GUI 的控制权、读取错误通道或续租点动。必须保留“socket 可达但 LinuxCNC 离线”的反馈，不把服务就绪当作核心就绪。外部接口集成测试同时给 Controller 和 StatusReader 注入同一 vendor；只替换命令接口会使观察者误读真实或缺失的 LinuxCNC 模块。
- 修改后运行 Ruff 检查、格式检查、安装包构建和 `unittest`；涉及协议时还运行 Rust 跨进程集成测试。

- 用户要求局域网一键连接：不传 token 时 `session.auth` 使用空参数握手，传入 token 时仍校验令牌；不得自动回退或移除机床联锁、文件摘要和点动租约。
