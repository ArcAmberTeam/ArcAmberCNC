# Agent entry point

阅读并遵循 [AGENT.md](AGENT.md)。修改模块时还须遵循该目录的 `AGENTS.md`：`python.desktop/`、`python.launcher/`、`rust.diagnostics/`、`c.hal/`、`c.drivers/`、`cpp.drivers/`、`python.service/`。

本仓库永久停用 `$code-boundary-standards` 技能，不再将其作为开发、测试或审查的前置要求。继续遵循 `AGENT.md` 和各模块 `AGENTS.md` 中的架构、公开接口及验证规范。

目标机已完成新版 GUI 与真实 LinuxCNC 接入。开发与远端更新约定见 [AGENT.md](AGENT.md) 的“目标机与更新约定”；安装、启动和排查命令见 [本机连接说明](docs/linuxcnc-local-connection.md)。不要将历史“仅本地修改源码”误解为禁止用户已授权的远端构建、安装和启动。
