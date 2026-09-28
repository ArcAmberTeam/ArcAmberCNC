# LinuxCNC Python 接口

[全项目模块地图](../../../../docs/module-map.md) · [执行协调层](../../task/README.md)

## 作用与语言

`emcmodule.cc` 是 C++ 编译扩展，对外使用方式为 `import linuxcnc`。提供 `command`、`stat`、`error_channel`、`ini`、`positionlogger` 及已有常量。Python 是调用语言，底层通道和扩展由 C++ 实现。

界面或未来的 Python 控制服务通过 NML 命令通道向 Task 提交操作，通过状态通道取得快照，通过错误通道取出消息。调用方不应依赖这个目录的文件布局。我们的 `backend/` 当前没有导入此模块，尚未接入机床。

## 职责边界

本模块原先放在 AXIS 目录中，现已独立保留；它不启动也不依赖 AXIS 界面。它提供 LinuxCNC 访问接口，不拥有我们新增服务的操作权或会话规则，也不执行实时伺服循环。

上游扩展中的 OpenGL `positionlogger` 仍供既有预览使用，已有 API 和 epoxy 链接依赖保留。独立命令工具归 `../python-tools/`，Tk/OpenGL 控件支持归 `../tk-support/`；两者都不是本模块的构建依赖。

修改扩展需要验证原生构建和 Python 导入/API 兼容性；新增服务的 socket 测试不能代替本扩展验证。
