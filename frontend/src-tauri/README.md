# Rust 桌面宿主与本地通信桥接

[全项目模块地图](../../docs/module-map.md) · [控制架构](../../docs/tauri-local-control-architecture.md) · [Python 服务](../../backend/README.md)

## 作用与语言

使用 Rust、Tauri 2、Tokio 和 Serde。负责桌面窗口启动、向网页开放有限命令、连接本机 Python 服务并校验返回消息。它属于非实时程序。

## 文件与入口

| 位置              | 作用                                          |
| ----------------- | --------------------------------------------- |
| `src/main.rs`     | 桌面可执行程序入口                            |
| `src/lib.rs`      | 构建 Tauri 应用，只注册 `service_health` 命令 |
| `src/service.rs`  | socket 路径、连接、超时、报文封装及返回校验   |
| `capabilities/`   | Tauri 能力配置                                |
| `tauri.conf.json` | 窗口、前端资源和打包配置                      |
| `tests/`          | Rust 与真实 Python 进程之间的诊断集成测试     |

Rust 库公开 `probe_service` 和 `ServiceHealth`；这不等于网页可以调用任意 Rust 函数。网页仅能调用注册的 Tauri 命令，不能提供任意 socket 路径。

## 通信与边界

上游为前端 `controller-session`，经 Tauri IPC 调用；下游为 Python 服务，经 Unix socket 通信。当前每次健康查询新建短连接，报文是四字节大端长度加 UTF-8 JSON，限长 65536 字节，总查询限时两秒。

只接受诊断模式且 `machine_connected: false` 的健康结果。没有机床命令、持续会话或状态推送，也不自动启动 Python 或 LinuxCNC。

未来 Rust 仍负责桌面权限及传输，Python 负责机床操作规则，LinuxCNC 负责运动。不能在 Rust 再复制一套回零或运行的业务判断；不能向网页暴露任意 Python 执行入口。

## 验证

在 `frontend/` 执行 `npm run desktop:check`、`npm run desktop:test`；打包执行 `npm run desktop:build`。涉及协议时同步验证 Python 安装包及跨进程测试。当前 CI 在 Debian 13 容器验证桌面构建，构建通过不表示机床已接通。
