# 项目架构与协作规范

## 范围与当前阶段

本仓库包含 LinuxCNC 源码；`VERSION` 当前为 2.9.10。新增 Web 界面位于 `frontend/`，与现有 `src/`、HAL 和实时运动代码独立。

项目维护和发布入口统一为 **`frontend/` Web 界面**。原生 AXIS 应用已删除，包括 Python 主程序、Tcl 界面、axis-remote、专属资源和构建/安装入口。现有 Web 界面及其独立资源保留。LinuxCNC 控制核心、共享 Python API 和其他上游工具保留，不属于当前 Web 发布产物。删除边界及遗留配置说明见 [迁移记录](docs/native-axis-removal.md)。

当前界面仍是机床操作原型；已加入 Tauri 桌面环境和独立 Python 诊断服务，通过 Unix socket 查询服务健康，但没有接入 LinuxCNC。机床动作只显示未接入说明；不得发送机床命令、读取硬件或声称完成了运动。服务启动由开发者显式执行，桌面不自动启动 LinuxCNC 或 Python。视觉设计不向原生 Tcl/Python 回写。

## 技术与系统边界

- 目标运行环境：Debian 13、Intel 核显。CPU 型号、LinuxCNC 安装版本和 WebKitGTK 能力仍须在目标机确认。
- 前端：Vue 3、TypeScript、Vite、Pinia、Reka UI、Tailwind CSS。用户已确定正式产品仅通过 Tauri 2 桌面程序操作；浏览器只用于界面预览和展示测试，不提供真实控制入口。
- 后续控制链路固定为 Vue → Tauri IPC → Rust → Unix domain socket → Python 控制服务 → LinuxCNC。不建设 HTTP/WebSocket 控制网关，不以 OpenAPI 作为本地消息协议；消息结构、版本与运行时校验仍须明确。详见 [Tauri 专用控制架构](docs/tauri-local-control-architecture.md)。
- LinuxCNC 自身负责插补、运动规划、实时线程及 HAL。Vue、Rust 与 Python 控制服务均不得承担实时伺服职责。Rust 拥有桌面权限和通信桥接；Python 拥有机床操作规则，不复制两套控制逻辑。
- 未来控制器进程持有应用内唯一命令写入口和错误通道读取入口。其他 UI/HALUI 的写权限需显式协调。预览解释工作放在独立进程。
- 不假设关闭 `DISPLAY` 后 LinuxCNC 仍运行；在接入前明确启动、关闭、重连及进程监管策略。
- 本阶段只提供有实际用途的 `health` 服务查询与对应 Tauri 命令；不创建假 WebSocket、未实现的控制命令或伪控制状态机。

## 模块边界

前端的具体目录及依赖见 [frontend/agent.md](frontend/agent.md)。功能模块采用扁平的 `src/packages/<name>/`：模块根文件为公开入口，子目录一律私有。跨模块和应用层只允许导入公开入口，包括 type-only 导入。禁止依赖环、反向依赖及生产代码引用测试夹具。

外部网络、文件、进程和平台接口只能由明确适配层拥有。后续 `controller-session` 负责会话、只读状态快照和命令生命周期；界面组件不得直接调用 LinuxCNC、HAL、HTTP、WebSocket 或 Tauri。

后续协议必须区分 joint/axis、机床/工件坐标、指令/实际位置、角度/长度单位；命令“已接受、已发送、已完成、结果未知”不得混为一谈。重连不得自动重放运动、MDI 或主轴命令。软急停 UI 不替代物理安全回路。

## README 人工维护规则

- 本仓库根目录及各级子目录中的 README 文档（文件名不区分大小写）仅允许人工维护，AI 不得自行新增、修改、删除或重命名。
- AI 在开发、重构、修复、补充文档、格式化或提交时，不得顺带更新 README，也不得用脚本、生成器或批量格式化间接改写。
- 发现 README 内容过时、链接失效或需要补充时，只说明建议，由人工修改；功能实现与 README 自动同步不属于 AI 的工作范围。
- 项目中文说明统一称 Tauri 部分为“桌面环境”，指本应用的窗口、网页运行环境及本地通信能力。

## 工作方式与验收

1. 写、改、设计、审查或测试代码前应用 `$code-boundary-standards`；先读本文件、子目录规范和已有实现。
2. 修改范围限于当前任务，保留用户已有改动；未经需求不要重构 LinuxCNC 原生代码。
3. 模块对外 API 小而明确；不创建通用 `utils` 垃圾桶，不为了测试暴露私有实现。
4. 从前端对照表链接的删除前 AXIS 源码提交核对按钮与条件项，来源记录在前端功能对照表。保留拷贝资产的许可证及来源。
5. 前端修改运行 `cd frontend && npm run check && npm run build`；影响交互时运行 `npm run test:e2e`，并目视检查页面。
6. 建立/调整边界规则时，临时加入非法深层导入，确认失败后删除，再确认正常代码通过。
7. 报告真实完成范围和验证结果；静态示意刀路不等于解释器结果或加工仿真。

## CI/CD 边界

所有活动 CI/CD job 均运行于 GitHub 托管的 `ubuntu-24.04` runner，不依赖 PVE 自托管 runner。源码检查通过 `.github/ci/setup-source-tools.sh` 验证预装工具并下载固定版本、校验 SHA-256 的 actionlint，不调用 apt/sudo。部署 job 仍通过 FRP 连接 Web 测试服务器。

当前唯一自动工作流为 `.github/workflows/ci.yml` 的 Desktop and Web CI：保留 Web 构建、浏览器测试和预览发布，新增 Python 3.11/3.13 安装包测试，以及 Debian 13 容器内的 Rust 格式/lint、Rust→Python 集成测试和 Tauri `.deb` 构建。所有任务纳入原有 `CI Gate`，保留分支部署策略。新增产物只上传 CI，不自动安装到机床；不构建或部署原生 LinuxCNC/AXIS `.deb`，不运行运动仿真。构建成功不代表机床控制或目标机图形已验收。

桌面 CI 的系统依赖与 Node/Rust 工具链由 `.github/ci/desktop/Dockerfile` 管理，使用 BuildKit 的 GitHub Actions 镜像层缓存；每次仍在新容器中运行 `.github/ci/desktop-in-container.sh` 检查当前源码。镜像不含应用源码，Rust 编译缓存随环境镜像 ID 隔离；缓存刷新和本地复现方式见 `.github/ci/README.md`。

`.github/ci/package-web.py` 拥有构建打包；`.github/staging/` 拥有传输、目标机安装和回滚。部署只能使用同一次 CI 已测试的产物。目标机新安装器和本机 Web 服务须按 staging README 一次性配置；修改仓库配置不代表已更新真实服务器。敏感凭据只进入部署 job。

架构研究背景：[docs/linuxcnc-ui-architecture-research-2026-09-21.md](docs/linuxcnc-ui-architecture-research-2026-09-21.md)。
