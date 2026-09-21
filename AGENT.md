# 项目架构与协作规范

## 范围与当前阶段

本仓库包含 LinuxCNC 源码；`VERSION` 当前为 2.9.10。新增 Web 界面位于 `frontend/`，与现有 `src/`、HAL 和实时运动代码独立。

项目维护和发布入口统一为 **`frontend/` Web 界面**。原生 AXIS 应用已删除，包括 Python 主程序、Tcl 界面、axis-remote、专属资源和构建/安装入口。现有 Web 界面及其独立资源保留。LinuxCNC 控制核心、共享 Python API 和其他上游工具保留，不属于当前 Web 发布产物。删除边界及遗留配置说明见 [迁移记录](docs/native-axis-removal.md)。

当前 Web 仍是静态原型，只实现菜单、标签、选择、输入、滚动和展示设置等本地界面行为。不得发送机床命令、启动控制进程、读取硬件或声称完成了运动。机床动作只显示未接入说明。视觉设计可在 Web 模块内部演进，不向原生 Tcl/Python 回写样式。

## 技术与系统边界

- 目标运行环境：Debian 13、Intel 核显。CPU 型号、LinuxCNC 安装版本和 WebKitGTK 能力仍须在目标机确认。
- 前端：Vue 3、TypeScript、Vite、Pinia、Reka UI、Tailwind CSS。桌面宿主未来采用 Tauri 2，当前先提供可独立运行的浏览器界面。
- 后续控制接入：Python LinuxCNC 适配器与 FastAPI 网关；LinuxCNC 自身负责插补、运动规划、实时线程及 HAL。Web/Rust/Python UI 网关均不得承担实时伺服职责。
- 未来控制器进程持有应用内唯一命令写入口和错误通道读取入口。其他 UI/HALUI 的写权限需显式协调。预览解释工作放在独立进程。
- 不假设关闭 `DISPLAY` 后 LinuxCNC 仍运行；在接入前明确启动、关闭、重连及进程监管策略。
- 不为静态阶段预建空服务、假 WebSocket、Tauri 命令或伪控制状态机。

## 模块边界

前端的具体目录及依赖见 [frontend/agent.md](frontend/agent.md)。功能模块采用扁平的 `src/packages/<name>/`：模块根文件为公开入口，子目录一律私有。跨模块和应用层只允许导入公开入口，包括 type-only 导入。禁止依赖环、反向依赖及生产代码引用测试夹具。

外部网络、文件、进程和平台接口只能由明确适配层拥有。后续 `controller-session` 负责会话、只读状态快照和命令生命周期；界面组件不得直接调用 LinuxCNC、HAL、HTTP、WebSocket 或 Tauri。

后续协议必须区分 joint/axis、机床/工件坐标、指令/实际位置、角度/长度单位；命令“已接受、已发送、已完成、结果未知”不得混为一谈。重连不得自动重放运动、MDI 或主轴命令。软急停 UI 不替代物理安全回路。

## 工作方式与验收

1. 写、改、设计、审查或测试代码前应用 `$code-boundary-standards`；先读本文件、子目录规范和已有实现。
2. 修改范围限于当前任务，保留用户已有改动；未经需求不要重构 LinuxCNC 原生代码。
3. 模块对外 API 小而明确；不创建通用 `utils` 垃圾桶，不为了测试暴露私有实现。
4. 从前端对照表链接的删除前 AXIS 源码提交核对按钮与条件项，来源记录在前端功能对照表。保留拷贝资产的许可证及来源。
5. 前端修改运行 `cd frontend && npm run check && npm run build`；影响交互时运行 `npm run test:e2e`，并目视检查页面。
6. 建立/调整边界规则时，临时加入非法深层导入，确认失败后删除，再确认正常代码通过。
7. 报告真实完成范围和验证结果；静态示意刀路不等于解释器结果或加工仿真。

## CI/CD 边界

当前唯一自动工作流为 `.github/workflows/ci.yml` 的 Web CI：前端类型/格式/模块边界检查、Vite 构建、产物浏览器测试和静态发布。保留 `CI Gate` 检查名与现有分支部署策略，检查原生 AXIS 删除边界，但不构建或部署 LinuxCNC/AXIS `.deb`，不运行 Tk 图标检查或运动仿真。

`.github/ci/package-web.py` 拥有构建打包；`.github/staging/` 拥有传输、目标机安装和回滚。部署只能使用同一次 CI 已测试的产物。目标机新安装器和本机 Web 服务须按 staging README 一次性配置；修改仓库配置不代表已更新真实服务器。敏感凭据只进入部署 job。

架构研究背景：[docs/linuxcnc-ui-architecture-research-2026-09-21.md](docs/linuxcnc-ui-architecture-research-2026-09-21.md)。
