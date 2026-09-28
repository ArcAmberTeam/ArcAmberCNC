# 进程通信与公共基础库

[全项目模块地图](../../docs/module-map.md)

## 作用与语言

C/C++，以 C++ 通信类为主。

提供 NML、CMS、RCS 等消息及通道基础设施；目录还包含 INI 读取、位姿数学等上游公共支持代码。

## 关键代码与通信

`nml/`、`cms/`、`rcs/` 管通信基础；`inifile/` 管配置读取；`posemath/` 管位姿数学。

由 LinuxCNC 消息定义和控制进程使用；本机 NML 配置可使用共享内存通道。它与 Task↔Motion 的专用运动共享内存接口需要区分。

## 职责边界

不拥有机床运行规则，不是前端网络服务。我们的 Unix socket 用于 Rust↔Python，没有替换 LinuxCNC 内部 NML。

这是保留的 LinuxCNC 核心代码，不属于当前 Web 静态构建产物。我们的 Python 服务尚未接入这些控制路径。此说明描述现有职责，不新增接口或改变上游依赖。

修改此处需要相应的 LinuxCNC 原生构建与功能验证；Web 或 Tauri 构建通过不能证明该模块可运行。涉及实时行为还需目标 Linux 主机验证。
