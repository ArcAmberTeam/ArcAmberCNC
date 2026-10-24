# Python 本地服务边界

先遵循根目录 `AGENT.md` 和 `$code-boundary-standards`。

- 本目录是独立 Python 包；不导入前端实现，也不依赖原生 AXIS。
- v1 `health` 保持历史诊断格式；v2 提供单写入者控制会话、状态、命令和隔离预览。`machine.status` 允许未附着的本地观察者读取新鲜状态，不获取控制权或续租点动。不得伪造反馈，也不启动 LinuxCNC。
- 公开入口为 `betterlinuxcnc_service`（`main`、`serve` 与 `python -m betterlinuxcnc_service`）、`bettercnc_controller.Controller`、`bettercnc_controller.StatusReader`、`bettercnc_preview.parse_program` 与预览 CLI、`bettercnc_cam_link`（`main`、`serve` 与 CAM 联动 CLI）；下划线文件为私有实现。
- service 只依赖 controller/preview 的公开入口。controller 拥有机床规则、文件写入和 LinuxCNC 命令/错误通道；preview 在独立进程调用 LinuxCNC 的 `gcode` 扩展，不复制解释器。两者不能反向依赖传输层或 Qt。
- 所有 Controller 调用在一个工作线程串行执行。点动必须有会话租约，失联停止本会话点动并取消未发送步骤，任何未知结果都不得自动重试。机床文件写入必须在最新状态校验后执行，不能信任客户端 capability。
- `StatusReader` 只拥有 `linuxcnc.stat`，与 Controller 在服务工作线程串行调用；不得创建命令或错误通道。`bettercnc_cam_link` 是独立进程，只依赖标准库，拥有网络收件及独立 inbox，通过公开 Unix 协议仅查询 `machine.status`，不得导入控制服务实现、LinuxCNC 或 Qt。上传成功不等于加载或加工完成，不远程启动加工。协议见 `../docs/cam-link-protocol.md`。
- CAM Link 的三个能力目录为 `protocol`、`receiver`、`feedback`，各自 `__init__.py` 为公开入口。根目录只组合启动、认证、连接及可选 UDP 发现调度；`protocol` 不依赖业务，`receiver` 和 `feedback` 只依赖 `protocol`，分别拥有程序/发现回复接收和回执/状态/发现广播发送。目录之间禁止私有深层导入或反向依赖。外部协议为独立的 TCP v2 长连接，24 字节帧头包含 `CAM2`、16 字节 ASCII 类型和正文长度，类型必须与正文方法一致；内部 `machine.status` 仍使用本地 v2 Unix 协议。
- `DiscoveryOptions` 是 CAM Link 的公开发现配置入口。UDP 发现显式开启，使用稳定设备 UUID，发送 `ANNOUNCE`，仅对匹配设备与近期随机数的 `DISCOVER_REPLY` 单播 `DISCOVER_ACK`。发现不携带令牌、文件或加工状态，不授予 TCP 认证或控制权，也不主动向 CAM 建立连接；关闭服务需停止广播并释放 UDP socket。
- 测试从公开对象、安装后的 CLI 和 socket 观察行为；允许注入 vendor 模块、时钟和预览进程工厂，不导入私有文件。真实 gcode 测试仅解释临时程序，不启动模拟器或硬件。
- 修改后运行 Ruff 检查、格式检查、安装包构建和 `unittest`；涉及协议时还运行 Rust 跨进程集成测试。
