# Python 本地服务边界

先遵循根目录 `AGENT.md` 和 `$code-boundary-standards`。

- 本目录是独立 Python 包；不导入前端实现，也不依赖原生 AXIS。
- 当前只实现 `health` 查询，不导入 LinuxCNC、不接受机床动作、不伪造反馈。
- `betterlinuxcnc_service` 和 `python -m betterlinuxcnc_service` 是公开入口；下划线文件为私有实现。
- 协议解析归 `_protocol.py`，socket 和进程信号生命周期归 `_server.py`；未来机床接入需要独立所有者，不塞入传输处理器。
- 测试从安装后的 CLI 和 socket 观察行为，不导入私有文件。
- 修改后运行 Ruff 检查、格式检查、安装包构建和 `unittest`；涉及协议时还运行 Rust 跨进程集成测试。
