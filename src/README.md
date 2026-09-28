# LinuxCNC 原生源码导航

[全项目模块地图](../docs/module-map.md)

本目录保存 LinuxCNC 控制核心及相关工具。仓库版本见根目录 `VERSION`。新增 Vue 界面位于 `../frontend/`，新增 Python 本地服务位于 `../backend/`；它们没有替换这里的运动实现。

| 模块                                                   | 职责                            |
| ------------------------------------------------------ | ------------------------------- |
| [Task](emc/task/README.md)                             | 任务和程序执行协调              |
| [G 代码解释器](emc/rs274ngc/README.md)                 | 程序语义及规范动作              |
| [轨迹规划](emc/tp/README.md)                           | 运动段队列、速度和衔接          |
| [实时运动](emc/motion/README.md)                       | 周期运动、回零及运动反馈        |
| [运动学](emc/kinematics/README.md)                     | 轴坐标与关节位置转换            |
| [外围动作](emc/iotask/README.md)                       | 换刀等 I/O 协调与握手           |
| [消息定义](emc/nml_intf/README.md)                     | LinuxCNC 内部消息和规范动作接口 |
| [Python 接口](emc/usr_intf/python-interface/README.md) | Python 访问 LinuxCNC 的编译扩展 |
| [NML 基础库](libnml/README.md)                         | 通信及公共支持代码              |
| [HAL](hal/README.md)                                   | 信号、控制组件和设备驱动        |
| [RTAPI](rtapi/README.md)                               | 实时运行环境适配                |

这些是控制主链路的模块导航，不覆盖每个上游工具和驱动子目录。`emc/usr_intf/` 仍保留 QtVCP、Gmoccapy 等工具；已删除的是原生 AXIS 及专属入口，不能理解为全部原生界面都已删除。
