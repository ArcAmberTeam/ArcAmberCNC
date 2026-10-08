# 项目架构与协作规范

## 范围与当前阶段

本仓库包含 LinuxCNC 源码；`VERSION` 当前为 2.9.10。原生 Qt Quick/PySide6 界面位于 `python.qt/`，本地 Rust 通信位于 `rust.socket/`，HAL 位于 `c.hal/`，设备驱动按主要实现语言分为 `c.drive/` 和 `cpp.drive/`。Python 控制服务保留在 `backend/`，混合编译的原生核心仍在 `src/`。

2026-10-08 用户决定删除 Web 并按“语言.职责”整理项目。**`python.qt/` 是正式桌面入口**，Vue/Web、Tauri 桌面环境及部署脚本已删除；Web 源码及设计资料整体删除，历史内容从 Git 获取。Rust v1 诊断逻辑提取为独立 `rust.socket/`，不替换现有 Python v2 控制链路。原生 AXIS 应用已删除，包括 Python 主程序、Tcl 界面、axis-remote、专属资源和构建/安装入口。LinuxCNC 控制核心、共享 Python API 和其他上游工具保留，不属于当前界面发布产物。删除边界及遗留配置说明见 [迁移记录](docs/native-axis-removal.md)，当前桌面决策见 [Qt 迁移说明](docs/qt-qml-migration.md)。

用户随后要求全部接入，并明确先使用 Unix socket、不运行模拟。Qt 入口现通过独立 Python 控制服务接入 LinuxCNC 状态、命令及解释器预览；独立 `rust.socket` 仍只查询 v1 诊断接口。服务由用户显式启动，桌面不自动启动 LinuxCNC 或 Python 服务。没有机床配置或实测依据时，不得声称完成了运动或目标机验收。视觉设计不向原生 Tcl/Python 回写。

## 技术与系统边界

- 目标运行环境：Debian 13、Intel 核显。CPU 型号、LinuxCNC 安装版本、Qt 图形后端、字体与缩放仍须在目标机确认。
- 原生桌面：Qt 6.8+、Qt Quick/QML、PySide6、Python 3.11+ 和 CMake；C++17 仅用于 Qt Quick Test 启动器。Web 应用已经删除；QML 和 Python 的职责及已有控制实现保持不变。
- 控制链路为 QML → PySide6 QObject → Unix domain socket → 独立 Python 控制服务 → LinuxCNC。桌面不得直接导入 LinuxCNC。已删除的 Vue/Tauri 链路历史决策见 [Tauri 架构记录](docs/tauri-local-control-architecture.md)。不建设 HTTP/WebSocket 控制网关；v2 协议见 [本地控制协议](docs/local-control-protocol.md)。
- LinuxCNC 自身负责 G 代码解释、插补、运动规划、实时线程及 HAL。QML、PySide6、Rust 与 Python 控制服务均不得承担实时伺服职责。桌面适配层拥有窗口和通信桥接；服务拥有机床操作规则，不复制两套控制逻辑。
- 控制服务持有应用内唯一命令写入口和错误通道读取入口。其他 UI/HALUI 的写权限仍需协调；检测到回执序号被其他写入者推进时取消后续命令步骤。预览在独立进程调用 LinuxCNC 的 `gcode` 扩展。
- 服务和桌面均不监管或启动 LinuxCNC；不假设退出 `DISPLAY` 后 LinuxCNC 仍运行。断开时取消未发出的命令并停止本会话点动，不自动中止已经运行的程序，重连不重放命令。
- v1 `health` 继续保持历史诊断格式，不能用于判断机床连接；真实状态只来自 v2 会话。离线坐标显示未知，测试夹具不得进入生产数据流。

## 模块边界

Qt 目录及依赖见 [python.qt/AGENTS.md](python.qt/AGENTS.md)：按 `BetterCnc.<Capability>` 命名模块及 `qmldir` 公开类型组织，组件通过公开状态与信号组合。Rust 的 `src/lib.rs` 为公开入口，内部通信实现私有，规范见 `rust.socket/AGENTS.md`。跨模块和应用层只允许导入公开入口，禁止依赖环、反向依赖及生产代码引用测试夹具。

顶层采用 `<language>.<role>`，语言表示实现主体，不拆散混合语言的能力。模块内先按功能、设备或总线划分，仅有实际实现差异才增加平台/CPU 子目录；不复制通用代码或建空架构目录。`rust.drive`、`rust.hal` 等只在实际引入实现时创建。目录与公开入口见 [模块地图](docs/module-map.md)。

原生核心仍从 `src/` 统一构建。`src/hal`、`c.hal/drivers` 和迁移驱动的旧位置保留相对符号链接，适配上游 Make、生成器及头文件路径；真实源码只归一个新模块。HAL 私有头与既有运行时的耦合属于记录在各模块 AGENTS 中的遗留例外，不因迁移扩大公开接口。

外部网络、文件、进程和平台接口只能由明确适配层拥有。Qt 的 `bettercnc.desktop` 向 QML 提供只读状态和操作，`bettercnc.session` 负责 socket；服务的 `bettercnc_controller` 拥有控制规则与机床文件写入，`bettercnc_preview` 拥有隔离解释。`rust.socket` 独立拥有 v1 诊断传输，不嵌入 Qt 控制链路。界面组件不得直接调用 LinuxCNC、HAL、socket、HTTP 或 WebSocket。

协议必须区分 joint/axis、机床/工件坐标、指令/实际位置、角度/长度单位；命令“已接受、已发送、已完成、结果未知”不得混为一谈。重连不得自动重放运动、MDI 或主轴命令。软急停 UI 不替代物理安全回路。测试不启动模拟器或机床；使用 vendor 接口替身、真实 Unix socket 和只解释文件的 LinuxCNC `gcode` 扩展。

## README 人工维护规则

- 本仓库根目录及各级子目录中的 README 文档（文件名不区分大小写）仅允许人工维护，AI 不得自行新增、修改、删除或重命名。
- AI 在开发、重构、修复、补充文档、格式化或提交时，不得顺带更新 README，也不得用脚本、生成器或批量格式化间接改写。
- 发现 README 内容过时、链接失效或需要补充时，只说明建议，由人工修改；功能实现与 README 自动同步不属于 AI 的工作范围。
- 项目中文说明统一称 Tauri 部分为“桌面环境”，指本应用的窗口、网页运行环境及本地通信能力。

## 工作方式与验收

1. 写、改、设计、审查或测试代码前应用 `$code-boundary-standards`；先读本文件、子目录规范和已有实现。
2. 修改范围限于当前任务，保留用户已有改动；未经需求不要重构 LinuxCNC 原生代码。
3. 模块对外 API 小而明确；不创建通用 `utils` 垃圾桶，不为了测试暴露私有实现。
4. 从 Git 中删除前的 `frontend/docs/axis-parity.md` 核对 AXIS 按钮、条件项及来源。保留拷贝资产的许可证及来源。
5. Qt 修改运行 CMake、CTest、Python 公共接口测试及受影响 QML 的 qmllint；改变交互或布局时目视验收，详见 `python.qt/AGENTS.md`。Rust 修改运行 fmt、check、clippy 与跨进程协议测试。原生迁移还需运行目录/归档/负向检查与受影响模块 CI。
6. 建立/调整边界规则时，临时加入非法深层导入，确认失败后删除，再确认正常代码通过。
7. 报告真实完成范围和验证结果；静态示意刀路不等于解释器结果或加工仿真。

## CI/CD 边界

所有活动 CI job 均运行于 GitHub 托管的 `ubuntu-24.04` runner，不依赖 PVE 自托管 runner。源码检查通过 `.github/ci/setup-source-tools.sh` 验证预装工具并下载固定版本、校验 SHA-256 的 actionlint，不调用 apt/sudo。所有自动和手动部署入口已经删除。

当前唯一自动工作流为 `.github/workflows/ci.yml` 的 ArcAmberCNC Module CI，push 覆盖 `main`、`staging测试环境` 和 `kihon`，同时支持 PR、merge queue 与手动运行。每个模块显示独立的“语言：功能”检查结果，矩阵设置 `fail-fast: false`；统一 `CI Gate` 要求全部矩阵实例通过，名称保持不变以兼容分支保护。

- C：HAL 抽象层、实时运动控制、硬件驱动；C++：LinuxCNC 任务层、G代码解析层、Python 扩展，共六个独立构建实例。入口为 `.github/ci/native-check.sh`，CI 专用目标文件复用原生 Makefile 依赖图，Debian 13 amd64 uspace 构建环境由 `.github/ci/native/Dockerfile` 管理。模块之间的编译依赖保留；不把独立 CI 误解成完全无依赖的库。
- Python：独立控制服务（3.11/3.13）、预览适配、Qt 界面后端；各自安装当前源码生成的 wheel 并运行所属测试，入口为 `.github/ci/python-check.sh`。预览 job 强制要求 Debian 的真实 `gcode` 扩展存在，缺失时失败；原生 Python 扩展 job 则验证当前源码编译的扩展，不混淆两者。
- QML：Qt 桌面界面；执行 QML UI、qmllint、模块边界与启动检查。`python.qt/scripts/ci-check.sh --suite desktop|qml` 为拆分入口，无参数仍运行完整 Qt 检查。
- HAL/INI/Tcl：机床配置与模块连接；静态检查配置语法、常用 HAL 命令参数、本地文件引用和 include 环。Tcl 只检查语法完整性，不执行文件。历史诊断在 `.github/ci/config-baseline.json` 中逐项记录原因和文件 SHA-256，新增诊断、历史文件变化或已修复但未移除的记录均导致失败。
- Rust：独立 `rust.socket` 库的 fmt、check、clippy 与 v1 Python 协议集成测试，固定工具链和锁文件。Web/Tauri 构建、浏览器测试、制品发布和部署 job 已删除。

CI 不启动 LinuxCNC、HAL 实时线程、模拟器或硬件。原生 HAL/运动/驱动以编译、链接和导出符号检查为主，任务层检查构建与动态依赖；解释器只运行独立文件解释回归。配置静态检查不能验证实际引脚存在、信号类型、单写入者、时序或机床参数正确性。原生构建仅上传日志，不发布 LinuxCNC 核心 `.deb`；Qt CI 只构建和测试并保留诊断，不打包发布或安装到目标机。构建成功不代表机床控制或目标机图形已验收。

Qt job 在独立 Debian 13 容器调用 `python.qt/scripts/ci-check.sh`，Python wheel 的构建与安装仅用于验证当前源码的可安装性，依赖安装只发生在 CI 环境。Rust job 独立验证通信库，无 Node、WebKitGTK 或 Tauri 依赖。所有分支及手动运行均仅承担构建、测试和诊断上传，不包含服务器部署、发布或安装到机床步骤。

架构研究背景：[docs/linuxcnc-ui-architecture-research-2026-09-21.md](docs/linuxcnc-ui-architecture-research-2026-09-21.md)。
