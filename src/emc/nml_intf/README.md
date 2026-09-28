# LinuxCNC 消息与规范动作定义

[全项目模块地图](../../../docs/module-map.md)

## 作用与语言

C/C++。

定义 LinuxCNC 命令、状态、消息格式、规范动作和相关公共结构，供 Task、界面接口及 I/O 等模块协作。

## 关键代码与通信

`emc.hh`、`emc_nml.hh` 定义消息；`emc.cc` 提供消息格式处理；`canon.hh` 定义解释器规范动作；`interpl.hh` 管解释命令列表接口。

依赖底层 NML／RCS 基础库；被 LinuxCNC 各控制进程使用。

## 职责边界

这是 LinuxCNC 内部契约，不是我们的 Rust↔Python JSON 协议。新增一个网页字段通常不需要修改这些内部消息。

这是保留的 LinuxCNC 核心代码，不属于当前 Web 静态构建产物。我们的 Python 服务尚未接入这些控制路径。此说明描述现有职责，不新增接口或改变上游依赖。

修改此处需要相应的 LinuxCNC 原生构建与功能验证；Web 或 Tauri 构建通过不能证明该模块可运行。涉及实时行为还需目标 Linux 主机验证。
