# 项目架构与协作规范

## 范围与当前阶段

本仓库包含 LinuxCNC 源码；`VERSION` 当前为 2.9.10。原生 Qt Quick/PySide6 界面位于 `app/desktop/`，Rust CAM 服务位于 `app/cam-link/`，应用 Release 更新器位于 `app/updater/`，Mesa 检查与独立烧录门禁位于 `app/mesa-update/`，本地诊断通信位于 `tools/diagnostics/`，HAL 位于 `src/hal/`，设备驱动按设备职责归入 `src/hal/drivers/` 和 `src/hal/user_comps/`。Python 控制服务保留在 `app/controller/`，混合编译的原生核心仍在 `src/`。

应用发布版本为 `26.10.26.6`，计划 Release 名称 `demo v26.10.26.6`、tag `v26.10.26.6`；它与原生核心版本独立。专用机配置工具位于 `tools/appliance/`。2026-10-26 用户明确限定：本地及目标机均禁止构建，本地 Docker 也禁止；只由 GitHub 托管 CI 构建、测试和产包。目标机下载 CI 已完成的 `.deb`，只做安装、运行与现场验收，不安装编译工具或执行源码测试。不得为恢复工作重新创建本地或目标机构建缓存。

2026-10-08 用户决定删除 Web；2026-10-25 将应用按职责收敛到 `app/`，原生 HAL 和驱动恢复上游实体目录。**`app/desktop/` 是正式桌面入口**，Vue/Web、Tauri 桌面环境及部署脚本已删除；Web 源码及设计资料整体删除，历史内容从 Git 获取。Rust v1 诊断逻辑提取为独立 `tools/diagnostics/`，不替换现有 Python v2 控制链路。原生 AXIS 应用已删除，包括 Python 主程序、Tcl 界面、axis-remote、专属资源和构建/安装入口。LinuxCNC 控制核心、共享 Python API 和其他上游工具保留，不属于当前界面发布产物。删除边界及遗留配置说明见 [迁移记录](docs/native-axis-removal.md)，当前桌面决策见 [Qt 迁移说明](docs/qt-qml-migration.md)。

用户随后要求全部接入，并明确先使用 Unix socket、不运行模拟。Qt 入口现通过独立 Python 控制服务接入 LinuxCNC 状态、命令及解释器预览；独立 `tools/diagnostics` 仍只查询 v1 诊断接口。独立 `app/launcher/` 可由用户显式调用，统一编排控制服务、原生 LinuxCNC 和 CAM 联动；桌面和服务本身不启动彼此或核心。没有机床配置或实测依据时，不得声称完成了运动或目标机验收。视觉设计不向原生 Tcl/Python 回写。

2026-10-25 已在目标机完成新版 GUI、控制服务和启动器安装，通过 `DISPLAY=:0` 显示 1024×600 界面，并从真实 LinuxCNC 读取连接状态；用户确认可以使用。验证覆盖安装版本、窗口显示和控制链路，不代表回零、点动、主轴、换刀或加工验收。无硬件开发使用外部 vendor 接口注入，不以测试数据冒充生产反馈。

## 技术与系统边界

- 目标运行环境：Debian 13、Intel 核显。已核实目标机 Python 3.13.5、PySide6 6.8.2.1、实时内核和 X11 `DISPLAY=:0`；CPU 型号、实际 GPU/Qt 渲染后端、LinuxCNC 安装版本和其他缩放组合仍需按需核实，不能由仓库 VERSION 推断安装版本。
- 原生桌面：Qt 6.8+、Qt Quick/QML、PySide6、Python 3.11+ 和 CMake；C++17 仅用于 Qt Quick Test 启动器。Web 应用已经删除；QML 和 Python 的职责及已有控制实现保持不变。
- 控制链路为 QML → PySide6 QObject → Unix domain socket → 独立 Python 控制服务 → LinuxCNC。桌面不得直接导入 LinuxCNC。已删除的 Vue/Tauri 链路历史决策见 [Tauri 架构记录](docs/tauri-local-control-architecture.md)。不建设 HTTP/WebSocket 控制网关；v2 协议见 [本地控制协议](docs/local-control-protocol.md)。
- LinuxCNC 自身负责 G 代码解释、插补、运动规划、实时线程及 HAL。QML、PySide6、Rust 与 Python 控制服务均不得承担实时伺服职责。桌面适配层拥有窗口和通信桥接；服务拥有机床操作规则，不复制两套控制逻辑。
- 控制服务持有应用内唯一命令写入口和错误通道读取入口。其他 UI/HALUI 的写权限仍需协调；检测到回执序号被其他写入者推进时取消后续命令步骤。预览在独立进程调用 LinuxCNC 的 `gcode` 扩展。
- 服务和桌面均不监管或启动 LinuxCNC；不假设退出 `DISPLAY` 后 LinuxCNC 仍运行。断开时取消未发出的命令并停止本会话点动，不自动中止已经运行的程序，重连不重放命令。
- v1 `health` 继续保持历史诊断格式，不能用于判断机床连接；真实状态只来自 v2 会话。离线坐标显示未知，测试夹具不得进入生产数据流。

## 模块边界

`app/launcher/` 是 Python 标准库的独立编排入口，默认读取 `/etc/betterlinuxcnc/launcher.json`。安装后的 `betterlinuxcnc-launch --kiosk-session` 维持专用 X11 会话，并通过 systemd 用户服务依次启动控制服务、原生 `linuxcnc <ini>` 与 CAM 联动。就绪探测只查询公开 v2 `machine.status`，不获取控制会话。模块保活不重放命令；原生核心重启必须确认旧进程组与原生锁已释放。`BETTERCNC_PROJECT_DIR` 仍是构建接口，但正式专用机发布固定使用 `/etc/betterlinuxcnc`，以匹配 root 更新服务的配置约束。安装包不导入或覆盖机床配置。

`tools/appliance/` 拥有固定账户/目录配置、显式机床迁移与维护接口。DEB 的唯一固定 `postinst` 调用 `provision`，幂等创建或校验专用账户和目录，不设置密码、不导入机床配置、不激活登录策略或启动服务。`prepare` 显式复制已有机床配置到系统目录，保留原件；仅迁移后的副本调整运行数据路径、禁用外部编辑器和过滤器。`activate` 写入专用登录策略，不由安装包、GUI 或普通更新自动执行。操作账户 `linuxcnc` 与只读 SSH 维护账户 `cnc-maint` 分离，两者都不获得通用 sudo/root shell；root 仅用于显式配置和固定更新服务。密码只通过不回显的标准输入设置，不进入源码、命令参数、包、日志或文档。

固定 `betterlinuxcnc-appliance backup` 仅由 root 执行，不接收任意输入或输出路径。它将 `/etc/betterlinuxcnc`、`/var/lib/betterlinuxcnc/machine` 的参数/刀具表等可变数据，以及工具管理的固定主机策略保存到 root 私有的 `/var/lib/betterlinuxcnc/recovery/snapshots`，记录 SHA-256、应用版本与时间。新快照创建并校验成功后才清理旧快照，保留最近 3 份。不备份大型程序库、收件、缓存或账户密码，不自动恢复；同盘快照不能抵御磁盘故障，也不代替独立数据备份。

Qt 目录及依赖见 [app/desktop/AGENTS.md](app/desktop/AGENTS.md)：按 `BetterCnc.<Capability>` 命名模块及 `qmldir` 公开类型组织，组件通过公开状态与信号组合。Rust 的 `src/lib.rs` 为公开入口，内部通信实现私有，规范见 `tools/diagnostics/AGENTS.md`、`app/cam-link/AGENTS.md` 与 `app/updater/AGENTS.md`。跨模块和应用层只允许导入公开入口，禁止依赖环、反向依赖及生产代码引用测试夹具。

自有应用集中在 `app/`，按职责命名 `desktop`、`controller`、`cam-link`、`launcher` 和 `updater`；实现语言由模块构建清单声明，不进入目录名称。独立 v1 兼容诊断库放在 `tools/diagnostics/`。`src/` 保留 LinuxCNC 原生源码与构建体系；`docs/`、`tests/`、`configs/` 及上游资源目录保持既有职责。模块内按功能、设备或总线划分，仅有实际实现差异才增加平台/CPU 子目录。目录与公开入口见 [模块地图](docs/module-map.md)。

根 `CMakeLists.txt` 是产品应用的构建、测试、安装与打包组合入口，各应用模块拥有自身安装内容。它不编译或安装 LinuxCNC 原生核心；原生核心仍从 `src/` 统一构建。`src/hal/`、`src/hal/drivers/` 与 `src/hal/user_comps/` 均为实体目录，取消语言分类迁移产生的兼容链接。HAL 私有头与既有运行时的耦合仍属于各模块 AGENTS 中记录的遗留边界，不因整理目录扩大公开接口。

正式 DEB 通过 `BETTERCNC_BUILD_MESA_HOMING=ON` 单独构建固定的 `zhulong_homing.so`，适配层由 `tools/mesa-homing/` 拥有。它仅从当前 2.9.10 原生源码生成 headers/halcompile，不编译完整核心；vendor 输入固定在 `vendor/cnc-mesa/SOURCE.json`，不得修改快照文件。包内模块仅供上游核心版本 2.9.10，显式 `prepare` 必须验证核心与开发包版本、头文件和模块摘要；包 CI 的 Debian 2.9.4 仅用于安装生命周期检查，不加载模块。用户于 2026-10-26 提供 X/Y/Z 实测总行程 420/275/90 mm，可通过显式 `--zhulong-homing-travel-mm 420 275 90 --zhulong-xyz-only` 将完整回零配置合入现有配置副本；未知行程使用互斥选项 `--zhulong-inputs-only`。用户确认本机实际仅有 XYZ，三轴选项严格移除已审查的预留 ABC 配置；不传该选项的六轴配置仍保留全部真实回零联锁。安装和更新不能自动触发 HOME。ELF、公开 API harness 和 HDL 仿真不代表机床运动验收。

外部网络、文件、进程和平台接口只能由明确适配层拥有。Qt 的 `bettercnc.desktop` 向 QML 提供只读状态和操作，`bettercnc.session` 负责 socket；服务的 `bettercnc_controller` 拥有控制规则与机床文件写入，`bettercnc_preview` 拥有隔离解释。`tools/diagnostics` 独立拥有 v1 诊断传输，不嵌入 Qt 控制链路。界面组件不得直接调用 LinuxCNC、HAL、socket、HTTP 或 WebSocket。

协议必须区分 joint/axis、机床/工件坐标、指令/实际位置、角度/长度单位；命令“已接受、已发送、已完成、结果未知”不得混为一谈。重连不得自动重放运动、MDI 或主轴命令。软急停 UI 不替代物理安全回路。自动化回归测试不启动模拟器或机床；使用 vendor 接口替身、真实 Unix socket 和只解释文件的 LinuxCNC `gcode` 扩展。用户授权的目标机部署与联调按下节执行，不属于 CI 或替身测试。

## 目标机与更新约定

2026-10-26 用户授权合并 CAM 三能力拆分并发布 v6。上传只保存文件；显式独立回零与回零后加工分别由 `homing.rs` 和 `wf-transhoming.rs` 提交到单一 Controller，组合流程确认本次回零完成后才加载加工。旧 CAM 客户端需显式发起启动；上传不再隐式运行。v6 沿用 v5 回零参数，Mesa 仅递增配套发布元数据。本次授权发布，不包含目标机安装或自动运动。

2026-10-26 用户已测试 v4 并授权实现、PR 合并发布 v5，然后由本任务通过项目更新器安装目标机。v5 包含回零后边界浮点误差修复、独立慢退与 XYZ 同时回零、更新权限回归和专用会话防自动黑屏。X/Y 首次搜索 15 mm/s、Z 5 mm/s，首次退开 2、二次定位 1、最终退回 X/Y 5、Z 2 mm/s；三轴同 HOME_SEQUENCE=1。用户报告开关触发后余量 1–2 mm，按最小 1 mm 计算；首次并行测试明确同意卸刀、清空台面并确认全行程无干涉，实际验收仍待现场完成。

2026-10-26 用户已现场确认：原 joint 0 / stepgen.00 为实机 Y，正向向右；原 joint 1 / stepgen.01 为实机 X，正向向前；原 joint 2 / stepgen.02 为 Z，正向向下。v4 交换 XY 全部电机输出/反馈/使能与参数通道，Z STEP_SCALE 改为 -200，修正后 X+向前、Y+向右、Z+向上。回零为 X向后420mm、Y向左275mm、Z向下90mm，GPIO020/021/022；三轴搜索方向均为负，v4 软限位分别0～410、0～265、0～80，回零完成仍需用户实机验收。

固定 `provision` 新增已授权的单机配置升级：只接受 `tools/appliance/_axis_upgrade.py` 中逐文件 SHA-256 匹配的已安装 v1/v4 机床配置，并要求控制 socket/原生锁已消失、安装模块 ABI 和方向适配来源有效；完整目录通过 renameat2 原子交换。匹配新修订后幂等复核摘要；未知改动拒绝，不覆盖其他机床、参数、刀具表、程序、坐标偏置。维护脚本字节保持不变，以兼容旧更新器。普通 prepare 仍不猜测电机映射；只有这次现场观察对应的固定迁移记录电机核验标记，v5 将 HOME=0 保持不变、MIN_LIMIT=-0.1，仍距开关4.9 mm；运动验收标 pending-empty-table-parallel-test。v5 要启用自动回零入口，不能以禁用版冒充完成。

Mesa v5 正式源码已拥有 signed HOME_OFFSET 方向判断、独立 `joint.N.home-backoff-vel` 正值输入和整组失败取消，应用构建不再替换 C 算法文本。公开 API 单轴两种符号配置54场景、并行27场景在CI运行，后者模拟5 ms输入延迟并检查配置的制动预算；不能据此声称机械验证完成。vendor 快照只从同版正式发布导入，provenance 继续固定源码、头文件与构建适配摘要。

2026-10-26 用户再次明确：所有源码、配置、权限和迁移逻辑修复必须先进入仓库，通过 PR/CI/Release 后再由已发布包部署；不在目标机直接修改文件或临时打补丁。只读现场诊断可以继续。后续应用变更只沿现有 `kihon → main` 的 PR 流程，不新增工作分支；commit、PR 标题/正文、CI 工作流/job/step 名称和自有 CI 输出使用英文，机床文件名与已有分支引用不随语言调整改名。

首次安装完成后，用户要求后续目标机升级只能使用本项目更新功能安装 latest Release，不再手工安装应用 DEB 或复制文件替代升级。用户另行要求清理目标机旧源码、旧配置副本、预演目录和当前恢复备份；保留实际运行所需系统配置、机床参数、刀具表、程序和驱动。此清理授权不表示禁用未来更新的备份门禁。

Git 提交身份固定为 `IwakuraTorei <IwakuraTorei@outlook.com>`。本仓库只在已有 `kihon` 分支开发并推送，再以 PR 合并到 `main`；禁止创建新分支。配套 `ArcAmberTeam/CNC-Mesa` 仓库由负责该仓库的 agent 在已有 `main` 直接提交推送。两仓库 Release 使用配套版本，目标机只消费经过 GitHub CI 验证的发布产物。

CI 工作流、job、step 和自有检查输出使用英文，保留分支保护引用的 `CI Gate` 名称；提交说明、PR 标题与正文、Release 说明也统一使用英文。应用中文界面和现场中文文件名不因此改名。

- 开发源码在本地修改，通过 PR 合并到 `main`；需要发布的 PR 添加 `build-release` 标签。当前禁止本地和目标机构建，源码测试交给 GitHub CI。迁移前管理入口为 `teto@192.168.109.67`，旧仓库 `/home/teto/ArcAmberCNC` 仅保留为机床迁移输入；专用策略激活后的 SSH 入口为 `cnc-maint@192.168.109.67`。用户已授权推送、PR 合并、由 CI 发布 `demo v26.10.26.1`，以及目标机下载已完成安装包、安装和图形会话切换。这不包含运动或加工验收；凭据不写入仓库、脚本、日志或文档。
- 拉取前后核对 `git status`、当前分支、HEAD 和目标远端引用。曾出现 `origin/main` 已更新而工作分支仍停在旧提交的情况；优先快进，不用 reset/clean 丢弃目标机修改。保留本机 `launcher.json`、`configs/zhulong-v2/` 及已有 VERSION/changelog 修改，不将其混入其他提交。
- `git pull` 不更新安装文件。根 CMake/CPack 组合应用并生成 `betterlinuxcnc-qt_26.10.26.1_amd64.deb`；正式部署通过 apt/dpkg 安装，以保留包版本记录，不用源码路径或 PATH 覆盖替代安装。根 CMake 不编译或打包 LinuxCNC 核心，核心仍由独立系统包管理。Release 使用正式 latest 发布，不能标记 prerelease。
- 迁移输入仍是现有 `configs/zhulong-v2/烛龙V2.ini` 与项目 `launcher.json`。先用 `stage` 在新临时目录审查副本，再显式 `prepare`；不会覆盖旧项目。已准备的系统配置不重复导入。普通更新保留 `/etc/betterlinuxcnc`、程序、收件、刀具表、参数与日志；详细目录见 [本机连接说明](docs/linuxcnc-local-connection.md)。
- root 更新服务确认控制系统正常停止后、调用 apt 前，必须成功执行固定 `backup`。备份失败就拒绝安装，保留已有快照并报告错误；不以忽略备份失败或自动恢复绕过更新门禁。手工备份也应在正常停机后由可信 root 维护会话执行，`cnc-maint` 没有备份或恢复权限。
- `linuxcnc` 的 HOME 为 `/var/lib/betterlinuxcnc/home`，缓存为 `/var/cache/betterlinuxcnc/user`，日志为 `/var/log/betterlinuxcnc/launcher`。`/var/lib/betterlinuxcnc` 与 `/var/cache/betterlinuxcnc` 顶层由 root 拥有且不可被普通用户写入。运行时端点位于 `/run/user/<linuxcnc UID>/betterlinuxcnc/control.sock`，不能沿用旧账户的 UID 1000 或 Xauthority。
- 安装和切换会话前确认旧启动器、核心及服务已正常退出；不强杀控制核心。先核对配置，再由 LightDM 的专用 X11 会话启动用户服务。通过只读连接、私有 `state.json`、日志和实际窗口共同确认，不能只看 systemd active。`activate` 前保留已打开的 root 维护会话，在新 SSH 固定命令与图形会话验证完成前不关闭。
- 专用 SSH 只接受无参数的 `help`、`version`、`status`、`logs`、`diagnostics`；不提供 shell、TTY、上传、转发或任意命令。`activate` 会限制原有 `teto`、`root` 和 `linuxcnc` 的 SSH 与日常提权入口，系统 root 身份仍供固定更新服务使用。恢复依赖受控本机维护与 root 私有的策略备份，不把普通 SSH 维护账户当成管理员。
- 连接诊断只发送公开 `machine.status`，不附着控制会话、不续租点动；诊断结束不影响现有 GUI。服务可达与机床已连接分别判断。远端操作前重新读取当前机床状态，不把历史截图中的急停/使能状态当作当前状态。
- 完整命令、已验证部署记录及日志位置见 [LinuxCNC 本机连接说明](docs/linuxcnc-local-connection.md)。纯文档更新检查链接、内容一致性和 `git diff --check` 即可，不为文档更新重启机床或重跑全套硬件相关验证。

## README 人工维护规则

- 本仓库根目录及各级子目录中的 README 文档（文件名不区分大小写）仅允许人工维护，AI 不得自行新增、修改、删除或重命名。
- AI 在开发、重构、修复、补充文档、格式化或提交时，不得顺带更新 README，也不得用脚本、生成器或批量格式化间接改写。
- 发现 README 内容过时、链接失效或需要补充时，只说明建议，由人工修改；功能实现与 README 自动同步不属于 AI 的工作范围。
- 项目中文说明统一称 Tauri 部分为“桌面环境”，指本应用的窗口、网页运行环境及本地通信能力。

## 工作方式与验收

1. 写、改、设计、审查或测试代码前，先读本文件、子目录规范和已有实现；不再要求调用额外的边界规范技能。
2. 修改范围限于当前任务，保留用户已有改动；未经需求不要重构 LinuxCNC 原生代码。
3. 模块对外 API 小而明确；不创建通用 `utils` 垃圾桶，不为了测试暴露私有实现。
4. 从 Git 中删除前的 `frontend/docs/axis-parity.md` 核对 AXIS 按钮、条件项及来源。保留拷贝资产的许可证及来源。
5. 验证要求保持：根 CMake/CTest、Python 公共接口、受影响 QML 的 qmllint、Rust fmt/check/clippy 与跨进程测试；当前全部源码构建和测试限定于 GitHub 托管 CI，本地及目标机均不执行，也不用本地 Docker 代替。改变交互或布局另需目标机实际已安装应用的目视验收。原生迁移还需目录/归档/负向检查与受影响模块 CI。
6. 建立/调整边界规则时，临时加入非法深层导入，确认失败后删除，再确认正常代码通过。
7. 报告真实完成范围和验证结果；静态示意刀路不等于解释器结果或加工仿真。

## CI/CD 边界

所有 CI 与 Release job 均运行于 GitHub 托管的 `ubuntu-24.04` runner，不依赖 PVE 自托管 runner。源码检查通过 `.github/ci/setup-source-tools.sh` 验证预装工具并下载固定版本、校验 SHA-256 的 actionlint，不调用 apt/sudo。构建及真实安装回归只发生在 GitHub 的隔离容器；流水线不 SSH 部署或安装到机床。

`.github/workflows/ci.yml` 的 ArcAmberCNC Module CI 覆盖 `main`、`staging测试环境` 和 `kihon` 的 push，同时支持 PR、merge queue 与手动运行。每个模块显示独立的英文“Language - Function”检查结果，矩阵设置 `fail-fast: false`；统一 `CI Gate` 要求全部矩阵及正式 DEB 验收通过，名称保持不变以兼容分支保护。

`.github/workflows/release.yml` 只为已合并到 `main` 且带 `build-release` 标签的 PR 发布。它检查同一 merge SHA 的 main push CI Gate，通过只读接口取得唯一 DEB artifact；仅发布 job 有 `contents: write`，不检出或执行 PR 源码。发布前复核包版本、架构、SHA-256、源码提交及 tag，并要求 `ArcAmberTeam/CNC-Mesa` 同 tag 正式 Release 的 `mesa-release.json`、来源提交、源码/集成归档摘要一致。上传真实 `.deb`、`SHA256SUMS`、清单原字节与 `CNC_MESA_PAIR.json`，生成正式 latest Release。配对缺失时可待其发布后重跑失败 job，或从 `main` 手动提供同一已合并 PR 编号重试；不需要跨仓写权限或 PAT。没有标签、CI 未通过或包缺失时不发布；源码归档不能替代 DEB。

- C：HAL 抽象层、实时运动控制、硬件驱动；C++：LinuxCNC 任务层、G代码解析层、Python 扩展，共六个独立构建实例。入口为 `.github/ci/native-check.sh`，CI 专用目标文件复用原生 Makefile 依赖图，Debian 13 amd64 uspace 构建环境由 `.github/ci/native/Dockerfile` 管理。模块之间的编译依赖保留；不把独立 CI 误解成完全无依赖的库。
- Python：独立控制服务（3.11/3.13）、预览适配、Qt 界面后端；各自安装当前源码生成的 wheel 并运行所属测试，入口为 `.github/ci/python-check.sh`。预览 job 强制要求 Debian 的真实 `gcode` 扩展存在，缺失时失败；原生 Python 扩展 job 则验证当前源码编译的扩展，不混淆两者。
- Python 启动编排（3.11/3.13）包含 kiosk 会话与真实暂存安装回归；专用机维护策略（3.11/3.13）是独立 job，检查 `tools/appliance` 的 Ruff、格式与公开 CLI，纳入同一 `CI Gate`。
- QML：Qt 桌面界面；执行 QML UI、qmllint、模块边界与启动检查。`app/desktop/scripts/ci-check.sh --suite desktop|qml` 为拆分入口，无参数仍运行完整 Qt 检查。
- HAL/INI/Tcl：机床配置与模块连接；静态检查配置语法、常用 HAL 命令参数、本地文件引用和 include 环。Tcl 只检查语法完整性，不执行文件。历史诊断在 `.github/ci/config-baseline.json` 中逐项记录原因和文件 SHA-256，新增诊断、历史文件变化或已修复但未移除的记录均导致失败。
- Rust：`tools/diagnostics` 的 v1 诊断测试，`app/cam-link` 的 CAM2 TCP/UDP、作业与点动跨进程测试，`app/updater` 的 Release 校验和安装门禁，以及 `app/mesa-update` 的同版清单检查与烧录拒绝测试；均运行 fmt、check、clippy，固定工具链和锁文件。Web/Tauri 构建、浏览器测试与机床部署 job 已删除。
- Debian：根 CMake 在 Debian 13 amd64 容器构建 CAM、应用更新、Mesa 检查、Mesa 烧录门禁四个真实 Rust 二进制并生成完整 DEB；真实首次/重复安装检查账户、目录权限、密码和数据保留，再显式验证容器内 SSH/sudo 的有效限制与私有备份轮转。阻止依赖启动服务，不运行机床、显示会话或 SSH daemon。成功后上传以提交 SHA 命名的 DEB artifact。

CI 不启动 LinuxCNC、HAL 实时线程、模拟器或硬件。原生 HAL/运动/驱动以编译、链接和导出符号检查为主，任务层检查构建与动态依赖；解释器只运行独立文件解释回归。配置静态检查不能验证实际引脚存在、信号类型、单写入者、时序或机床参数正确性。原生构建仅上传日志，不发布 LinuxCNC 核心 `.deb`；Qt CI 只构建和测试并保留诊断，不打包发布或安装到目标机。构建成功不代表机床控制或目标机图形已验收。

Qt job 在独立 Debian 13 容器调用 `app/desktop/scripts/ci-check.sh`，Python wheel 的构建与安装仅用于验证当前源码的可安装性，依赖安装只发生在 CI 环境。Rust job 独立验证通信库，无 Node、WebKitGTK 或 Tauri 依赖。启动器暂存安装回归独立核对应用版本、架构、依赖和布局；正式 DEB job 另作真实安装验收。构建 workflow 不持有发布写权限，Release workflow 只发布经过同一提交验收的安装包；两者均不部署到目标机。

架构研究背景：[docs/linuxcnc-ui-architecture-research-2026-09-21.md](docs/linuxcnc-ui-architecture-research-2026-09-21.md)。

## Rust CAM 系统服务

`app/cam-link/` 替代 Python CAM Link，安装命令仍为 `betterlinuxcnc-cam-link`，启动器既有 `cam` 配置及 TCP 6522、UDP 8421 不变。网络进程通过 v2 Unix 协议接入单一 Python Controller，不引入第二个 LinuxCNC 命令写入者。构建安装步骤见 [CAM 协议与启动](docs/cam-link-protocol.md)。

Release 更新器由独立 `app/updater/` 拥有。GUI 只能请求固定 `betterlinuxcnc-system-update.service` 系统服务；root 服务独立查询正式 Release、下载并校验包，确认机床空闲且未使能后协调 `linuxcnc` 用户服务正常停止，再完成配置与机床数据备份，备份失败不安装。普通用户不能向 root 传入包路径、URL、版本或命令。应用版本取根 CMake/安装包及公开 `bettercnc.__version__`，不能使用核心 `VERSION`。协议和发布包约定见 [应用更新说明](docs/firmware-updates.md)。

`app/mesa-update/` 独立拥有 `betterlinuxcnc-mesa-update` 与 `betterlinuxcnc-mesa-flash`，检查/下载与 root 烧录入口分离。本版 CNC-Mesa 清单明确 `firmware.available=false`，没有新 ISE 位流，实施、时序和板上验收声明均为 false；这允许配套应用发布，但烧录入口必须拒绝实际写入。原厂 bit 不可作为更新载荷，也不能从参考源码归档提取后绕过清单。不得声称完成新的硬件验收。
