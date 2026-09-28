<h1 align="center">BetrerLinuxCNC</h1>

<p align="center">
  为 <strong>arcamber CNC 设备</strong>专门设计的 LinuxCNC。<br />
  以成熟的运动控制核心为基础，打造中文操作界面、现代桌面体验与职责清晰的本地控制架构。
</p>

<p align="center">
  <a href="docs/module-map.md">模块地图</a> ·
  <a href="frontend/README.md">前端开发</a> ·
  <a href="frontend/src-tauri/README.md">桌面环境</a> ·
  <a href="backend/README.md">Python 服务</a> ·
  <a href="src/README.md">控制核心</a>
</p>

<p align="center">
  <img src="https://skillicons.dev/icons?i=cpp,c,python,rust,ts,js,vue,tauri,pinia,vite&amp;theme=light&amp;perline=10" alt="C++、C、Python、Rust、TypeScript、JavaScript、Vue、Tauri、Pinia、Vite" />
</p>
<p align="center">
  <img src="https://skillicons.dev/icons?i=tailwind,html,css,nodejs,npm,linux,debian,docker,githubactions,git&amp;theme=light&amp;perline=10" alt="Tailwind CSS、HTML、CSS、Node.js、npm、Linux、Debian、Docker、GitHub Actions、Git" />
</p>
<p align="center">
  <img src="https://skillicons.dev/icons?i=bash,gtk,qt,md&amp;theme=light&amp;perline=4" alt="Bash、GTK、Qt、Markdown；Qt 属于保留的上游工具" />
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Reka_UI-34343B?style=flat-square" alt="Reka UI" />
  <img src="https://img.shields.io/badge/Tokio-34343B?style=flat-square" alt="Tokio" />
  <img src="https://img.shields.io/badge/Serde-34343B?style=flat-square" alt="Serde" />
  <img src="https://img.shields.io/badge/Playwright-34343B?style=flat-square" alt="Playwright" />
  <img src="https://img.shields.io/badge/Ruff-34343B?style=flat-square" alt="Ruff" />
  <img src="https://img.shields.io/badge/Prettier-34343B?style=flat-square" alt="Prettier" />
  <img src="https://img.shields.io/badge/dependency--cruiser-34343B?style=flat-square" alt="dependency-cruiser" />
</p>
<p align="center">
  <img src="https://img.shields.io/badge/GNU_Make-34343B?style=flat-square" alt="GNU Make" />
  <img src="https://img.shields.io/badge/Autotools-34343B?style=flat-square" alt="Autotools" />
  <img src="https://img.shields.io/badge/Meson-34343B?style=flat-square" alt="Meson" />
  <img src="https://img.shields.io/badge/Tcl%2FTk-34343B?style=flat-square" alt="Tcl/Tk" />
  <img src="https://img.shields.io/badge/OpenGL-34343B?style=flat-square" alt="OpenGL" />
  <img src="https://img.shields.io/badge/WebKitGTK-34343B?style=flat-square" alt="WebKitGTK" />
</p>

## 技术栈

| 范围           | 使用的技术                                                                                                     |
| -------------- | -------------------------------------------------------------------------------------------------------------- |
| 操作界面       | Vue 3、TypeScript、Pinia、Reka UI、Tailwind CSS、HTML/CSS、SVG                                                 |
| 前端工具       | Vite、Node.js、npm；JavaScript 用于工具配置与脚本                                                              |
| 桌面环境       | Tauri 2、Rust、Tokio、Serde；Linux 上使用 WebKitGTK                                                            |
| 本地服务       | Python 3.11+、asyncio、Unix socket、JSON；setuptools 构建安装包                                                |
| 控制核心       | C、C++、LinuxCNC Task、RS274NGC 解释器、轨迹规划、运动学、HAL、RTAPI、NML                                      |
| 系统与原生构建 | Linux、Debian 13、PREEMPT_RT；GNU Make、Autotools、Meson、Cargo                                                |
| 测试与质量     | Playwright、TypeScript 检查、dependency-cruiser、Prettier、Ruff、unittest、Rust 测试、Clippy、rustfmt          |
| 持续集成与部署 | Git、GitHub Actions、Docker / BuildKit、Bash、Python、SSH / rsync；工作流和脚本检查使用 actionlint、ShellCheck |
| 保留的上游工具 | Qt / PyQt、GTK、Tcl/Tk、OpenGL 等；独立于新增 Vue / Tauri 操作界面                                             |

图标使用 [Skill Icons](https://github.com/tandpfun/skill-icons)，补充标签使用 [Shields.io](https://shields.io/)。图标仅用于仓库文档，运行中的前端资源仍全部本地提供。

## 仓库架构

```text
frontend/
├── src/app/                  应用启动
├── src/pages/                页面布局与功能组合
├── src/packages/             按业务划分的八个前端模块
├── src-tauri/                Rust 桌面环境与本地通信桥接
└── tests/                    浏览器交互测试
backend/
├── src/betterlinuxcnc_service/ Python 本地服务
└── tests/                    安装包与服务协议测试
src/
├── emc/                      程序解释、执行协调与运动控制
├── hal/                      信号连接、控制组件与硬件驱动
├── rtapi/                    实时运行环境适配
└── libnml/                   内部通信与公共支持代码
docs/                         架构、模块导航和迁移说明
.github/                      持续集成、构建与预览部署
```

控制链路规划为：**Vue → Tauri IPC → Rust → Unix socket → Python → LinuxCNC → HAL → 设备**。界面负责展示和操作意图，Rust 负责桌面通信边界，Python 负责未来的机床操作流程，LinuxCNC 核心负责轨迹规划和实时运动。

**当前进度：** 中文界面与 Tauri 桌面环境已建立，Rust 与 Python 已实现健康查询；主页面未挂载诊断组件，Python 尚未接入 LinuxCNC。坐标、刀路和机床按钮仍是展示原型。原生 AXIS 已删除，LinuxCNC 核心、共享 Python 接口及其他上游工具保留。

## 开发与实现入口

| 方向          | 开发说明                                                                         | 实现代码                                                                                    |
| ------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Web 前端      | [安装、启动与验证](frontend/README.md)                                           | [应用源码](frontend/src/) · [浏览器测试](frontend/tests/)                                   |
| Tauri 桌面    | [桌面职责与通信](frontend/src-tauri/README.md)                                   | [Rust 源码](frontend/src-tauri/src/) · [跨进程测试](frontend/src-tauri/tests/)              |
| Python 服务   | [服务启动与协议](backend/README.md)                                              | [Python 源码](backend/src/betterlinuxcnc_service/) · [服务测试](backend/tests/)             |
| LinuxCNC 核心 | [原生源码导航](src/README.md)                                                    | [执行与运动](src/emc/) · [HAL](src/hal/) · [RTAPI](src/rtapi/)                              |
| CI/CD         | [持续集成说明](.github/ci/README.md) · [测试环境部署](.github/staging/README.md) | [工作流](.github/workflows/ci.yml) · [构建脚本](.github/ci/) · [部署脚本](.github/staging/) |

## 中文模块文档

每个模块的说明放在自身目录内，包含使用语言、作用、关键文件、上下游关系和职责边界。下面提供独立入口。

### 总体导航

- [全项目模块地图与通信链路](docs/module-map.md)
- [前端模块目录与依赖规则](frontend/src/packages/README.md)
- [LinuxCNC 原生源码导航](src/README.md)
- [Python 服务运行与协议说明](backend/README.md)

### 前端模块

| 模块         | 中文说明                                                                     | 实现入口                                                        |
| ------------ | ---------------------------------------------------------------------------- | --------------------------------------------------------------- |
| 应用启动     | [应用初始化和样式接入](frontend/src/app/README.md)                           | [app](frontend/src/app/)                                        |
| 页面组合     | [布局、分隔条与快捷键](frontend/src/pages/README.md)                         | [pages](frontend/src/pages/)                                    |
| 通用控件     | [控件、图标和视觉规范](frontend/src/packages/ui-system/README.md)            | [ui-system](frontend/src/packages/ui-system/)                   |
| 功能目录     | [菜单定义与演示数据](frontend/src/packages/axis-catalog/README.md)           | [axis-catalog](frontend/src/packages/axis-catalog/)             |
| 展示对话框   | [跨区域对话框状态](frontend/src/packages/axis-presentation/README.md)        | [axis-presentation](frontend/src/packages/axis-presentation/)   |
| 控制会话     | [桌面诊断入口与接入边界](frontend/src/packages/controller-session/README.md) | [controller-session](frontend/src/packages/controller-session/) |
| 手动操作     | [点动、主轴、冷却与倍率](frontend/src/packages/manual-control/README.md)     | [manual-control](frontend/src/packages/manual-control/)         |
| 加工程序     | [只读程序与行选择](frontend/src/packages/program-view/README.md)             | [program-view](frontend/src/packages/program-view/)             |
| 刀路与坐标   | [预览、数显及视图状态](frontend/src/packages/toolpath-view/README.md)        | [toolpath-view](frontend/src/packages/toolpath-view/)           |
| 菜单与工具栏 | [入口和对话框组合](frontend/src/packages/axis-chrome/README.md)              | [axis-chrome](frontend/src/packages/axis-chrome/)               |

### 桌面与本地服务

| 模块            | 中文说明                                                               | 实现入口                                                      |
| --------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------- |
| Rust 桌面环境   | [Tauri 权限与 socket 桥接](frontend/src-tauri/README.md)               | [src-tauri](frontend/src-tauri/)                              |
| Python 本地服务 | [协议解析与连接生命周期](backend/src/betterlinuxcnc_service/README.md) | [betterlinuxcnc_service](backend/src/betterlinuxcnc_service/) |

### LinuxCNC 控制核心

| 模块        | 中文说明                                                                     | 实现入口                                               |
| ----------- | ---------------------------------------------------------------------------- | ------------------------------------------------------ |
| Python 接口 | [Python 与 LinuxCNC 的编译扩展](src/emc/usr_intf/python-interface/README.md) | [python-interface](src/emc/usr_intf/python-interface/) |
| 任务执行    | [模式、程序和动作协调](src/emc/task/README.md)                               | [task](src/emc/task/)                                  |
| G 代码解释  | [程序语义、坐标与补偿](src/emc/rs274ngc/README.md)                           | [rs274ngc](src/emc/rs274ngc/)                          |
| 轨迹规划    | [速度、加减速与路径衔接](src/emc/tp/README.md)                               | [tp](src/emc/tp/)                                      |
| 实时运动    | [周期运动、点动与回零](src/emc/motion/README.md)                             | [motion](src/emc/motion/)                              |
| 运动学      | [轴坐标与关节位置转换](src/emc/kinematics/README.md)                         | [kinematics](src/emc/kinematics/)                      |
| 外围动作    | [换刀等 I/O 协调](src/emc/iotask/README.md)                                  | [iotask](src/emc/iotask/)                              |
| 消息定义    | [命令、状态与规范动作](src/emc/nml_intf/README.md)                           | [nml_intf](src/emc/nml_intf/)                          |
| 通信基础库  | [NML 与公共支持代码](src/libnml/README.md)                                   | [libnml](src/libnml/)                                  |
| 硬件抽象层  | [信号、组件与硬件连接](src/hal/README.md)                                    | [hal](src/hal/)                                        |
| 实时适配    | [实时任务和运行环境](src/rtapi/README.md)                                    | [rtapi](src/rtapi/)                                    |

## 架构、设计与交付

- [项目协作与架构规范](AGENT.md) · [前端架构规范](frontend/agent.md)
- [Tauri 专用本地控制架构](docs/tauri-local-control-architecture.md)
- [架构研究与技术选型](docs/linuxcnc-ui-architecture-research-2026-09-21.md)
- [前端视觉说明](frontend/docs/linear-visual-style.md)
- [中文 UI 设计交接](frontend/docs/ui-design/README.md)
- [AXIS 功能对照](frontend/docs/axis-parity.md)
- [原生 AXIS 移除范围与迁移](docs/native-axis-removal.md)

## 上游与许可证

本项目基于 [LinuxCNC](https://github.com/LinuxCNC/linuxcnc)；仓库中的控制核心版本标记见 [VERSION](VERSION)。许可证及各组件适用条款见 [COPYING](COPYING) 和对应文件声明，历史图标来源见 [资源说明](frontend/public/axis/NOTICE.md)。

[上游项目介绍与原始声明](docs/linuxcnc-upstream-readme.md) · [LinuxCNC 官方文档](https://linuxcnc.org/docs/2.9/html/)
