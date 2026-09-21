# 原生 AXIS 移除边界

本次移除的是原生 **AXIS GUI**。`frontend/` Web 原型保留，LinuxCNC 的解释器、轨迹规划、实时运动、HAL、驱动和运动学代码保留。运动控制里的 `axis` 表示坐标轴，不是待删除的界面。

## 已删除

- `src/emc/usr_intf/axis/` 的 AXIS 主程序、axis-remote、界面专用辅助文件和旧构建入口。
- `share/axis/` 的主窗口 Tcl、工具栏、启动图、界面配置和其他专属资源。
- `bin/profile_axis`、AXIS 专用 propertywindow、axis/axis-remote 命令手册。
- Makefile、Debian 文件清单及翻译手册清单中的 AXIS 安装条目；关闭流程不再调用 axis-remote。

## 共享能力的归属

| 模块 | 保留能力与公开入口 | 依赖方 |
| --- | --- | --- |
| `src/emc/usr_intf/python-interface/` | 构建 `lib/python/linuxcnc.so`；保留 `import linuxcnc` 的完整原有 API | Python 控制客户端、诊断工具、后续控制网关 |
| `src/emc/usr_intf/python-tools/` | 原有独立命令：mdi、linuxcnctop、hal_manualtoolchange、image-to-gcode、debuglevel 等 | HAL 配置和上游工具 |
| `src/emc/usr_intf/tk-support/` | 构建 `_togl.so`；通过已有 `rs274.OpenGLTk` 使用 | Vismach、已有预览组件 |
| `share/linuxcnc/tk-support/` | 通用 Tcl 对话框和三张消息图；Python 通过 `nf` 访问 | 换刀提示、程序生成工具 |

共享 Python 控制绑定源码原样迁移，未改动命令、状态、错误通道和 positionlogger API。现有绑定仍包含 OpenGL positionlogger，因此保留原链接依赖；这次不宣称把整个 LinuxCNC 构建改成无图形库版本。

QtVCP、Gmoccapy、Touchy、配置向导和独立诊断工具是其他上游程序，不属于 AXIS 主界面，本次没有删除。它们不进入 Web 构建或发布产物。保留通用 Tk 依赖是为了这些既有工具，不是保留 AXIS 的隐藏副本。

## 旧配置与历史资料

上游 INI/HAL 配置及用户手册保留为控制引擎开发和 Web 功能参考。指定 `DISPLAY = axis`（包括带路径的 axis/axis.py）的配置会在启动 HAL、实时组件和任务进程前退出，并说明 AXIS 已移除。未将旧配置自动转换为 Web 或其他控制界面。原来的 `send_to_axis` 回调保留失败返回值，让 pyngcgui 提示保存文件，不再启动远程命令。

需要运行控制引擎时，必须选择可用的控制入口并完成对应配置迁移。当前 Web 仍是静态原型，不能填写进 `DISPLAY` 来冒充控制会话。

前端图标和展示用 G-code 独立保存在 `frontend/`，来源链接固定到删除前的 Git 提交。历史文档、翻译记录中出现 AXIS 名称不表示该程序仍可构建或安装。

## 验证

Web CI 的 source-checks 包含 AXIS 移除边界、Makefile 目标和启动器拒绝旧配置的检查；前端类型、模块边界、构建及浏览器测试照常运行。轻量检查不替代 Linux 上的完整原生编译、安装和运行验收。
