# 模块职责与通信地图

[项目首页](../README.md) · [架构规范](../AGENT.md) · [控制协议与后续规划](tauri-local-control-architecture.md)

## 当前已经做到哪里

界面使用 Vue 和 TypeScript；桌面使用 Tauri 和 Rust；本地诊断服务使用 Python。Rust↔Python 已实现 Unix socket 健康查询，机床命令和持续状态推送尚未实现。主页面没有挂载诊断组件，不主动查询服务。

LinuxCNC 的 C/C++ 控制核心保留，但新增 Python 服务还没有连接它。按钮、坐标和刀路目前仍是展示原型。以下完整控制链路包含待接入部分，不能据此认为已可控制机床。

## 模块之间怎么联系

```text
Vue 功能界面
  → controller-session：前端统一通信入口
  → Tauri IPC：网页调用桌面命令
  → Rust：桌面权限与本机通信桥接
  → Unix socket：长度前缀 + JSON
  → Python：当前只提供 health；机床操作规则待实现
  ────────── 以下接入尚未完成 ──────────
  → linuxcnc Python 接口（C++ 编译扩展）
  → NML 命令通道
  → Task：协调程序解释、运动与外围动作
      → G 代码解释器：将程序变成规范动作
      → 运动接口／共享内存 → 实时运动 → 轨迹规划、运动学
      → I/O 控制：换刀等动作及握手
  → HAL 组件和驱动 → 控制卡、驱动器和传感器
```

状态沿相应通道返回：实时模块更新运动状态，Task 汇总；Python 接入后轮询 LinuxCNC 状态和错误，再通过 Rust 通知界面。具体持续状态协议仍待实现。

界面传递操作意图，不按伺服周期发送电机位置。实时运动不等待网页逐帧确认。Unix socket 是本机传输方式，不提供硬实时保证。Task↔Motion 的专用共享内存与 NML 通道需要区分；新应用不直接写运动共享内存。

## 从哪个目录看起

| 模块入口                                                               | 主要语言             | 拥有的职责                           |
| ---------------------------------------------------------------------- | -------------------- | ------------------------------------ |
| [应用启动](../frontend/src/app/README.md)                              | TypeScript、Vue      | 创建应用并接入样式                   |
| [页面组合](../frontend/src/pages/README.md)                            | Vue、TypeScript、CSS | 页面布局、分隔条、快捷键组合         |
| [八个前端功能模块](../frontend/src/packages/README.md)                 | Vue、TypeScript、CSS | 各自的业务展示状态与公开接口         |
| [Rust 桌面环境](../frontend/src-tauri/README.md)                       | Rust                 | 桌面命令边界和 socket 桥接           |
| [Python 服务](../backend/src/betterlinuxcnc_service/README.md)         | Python               | 当前诊断服务；未来机床操作与状态采集 |
| [LinuxCNC Python 接口](../src/emc/usr_intf/python-interface/README.md) | C++                  | 向 Python 提供 LinuxCNC 通道         |
| [Task](../src/emc/task/README.md)                                      | C++                  | 任务和程序执行协调                   |
| [G 代码解释器](../src/emc/rs274ngc/README.md)                          | C++                  | 程序语义、坐标和补偿                 |
| [轨迹规划](../src/emc/tp/README.md)                                    | C                    | 路径速度、加减速、段间衔接           |
| [实时运动](../src/emc/motion/README.md)                                | C 为主               | 周期运动计算、点动、回零             |
| [运动学](../src/emc/kinematics/README.md)                              | C 为主               | 轴坐标与关节位置转换                 |
| [外围动作](../src/emc/iotask/README.md)                                | C++                  | 换刀等外围动作协调                   |
| [内部消息定义](../src/emc/nml_intf/README.md)                          | C/C++                | 命令、状态和规范动作契约             |
| [NML 基础库](../src/libnml/README.md)                                  | C/C++                | LinuxCNC 通信及公共支持              |
| [HAL](../src/hal/README.md)                                            | C 为主               | 软件信号、组件和设备连接             |
| [RTAPI](../src/rtapi/README.md)                                        | C 为主               | 实时任务与运行环境适配               |

## 避免职责混在一起

- 改按钮颜色找 `ui-system`；改手动操作面板找 `manual-control`；不要建立全局组件或状态杂物目录。
- 改桌面权限和传输找 Rust；机床操作前置条件归未来 Python 控制层；LinuxCNC 仍保留自身执行约束。
- 改 G 代码含义找解释器；改路径速度规划找 `tp`；改机床结构的坐标转换找 `kinematics`。
- 改设备引脚连接与驱动找 HAL 和机床配置；不要从 Vue 绕过控制服务直接访问硬件。
- 前端公开入口规则由 dependency-cruiser 检查；这些新增文档不改变原有 C/C++ 模块接口或上游构建方式。

当前未建立独立 `protocol` 或 `desktop-platform` 前端模块，也没有真实控制状态机；它们仍是规划。原生 AXIS 已移除，但其他上游界面和工具仍保留，见 [删除边界](native-axis-removal.md)。
