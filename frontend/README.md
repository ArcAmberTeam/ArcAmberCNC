# BetterLinuxCNC Web

使用 Vue 3、TypeScript、Vite、Pinia、Reka UI 和 Tailwind CSS 开发独立 Web 界面。现有原型以 LinuxCNC **2.9.10** 的 AXIS 功能和布局为起点；原生 AXIS 应用已经删除，后续只维护 Web。

当前是 **UI 原型**。所有机床动作只展示未接入说明；不连接 LinuxCNC、HAL 或网络控制服务，不执行 G-code，不读写真实程序文件。黑色预览区的 SVG 是静态刀路示意，坐标和状态来自固定样例。

## 启动

使用 Node.js 24 LTS 和 npm，在仓库根目录运行：

```sh
cd frontend
npm ci
npm run dev
```

打开终端显示的本地地址，默认是 `http://127.0.0.1:5173`。开发服务仅绑定本机；端口占用时以 Vite 输出为准。

```sh
npm run check
npm run build
npm run test:e2e
```

`check` 包含 TypeScript、模块边界和格式检查；`build` 生成 `dist/`。首次运行浏览器测试时，如本机缺少 Playwright 的 Chromium，先执行 `npx playwright install chromium`。构建预览使用 `npm run preview`。

这些命令是验收入口，本文件本身不代表它们已经通过。目标环境是 Debian 13 + Intel 核显；macOS 浏览器中的检查不代表目标机 WebKitGTK、Tauri 或 LinuxCNC 集成已验收。

## 界面范围

- File、Machine、View、Help 菜单与子菜单，默认铣床工具栏。
- Manual Control / MDI、轴选择、点动入口、回零、对刀、主轴、冷却和倍率控件。
- Preview / DRO、显示选项、只读 G-code 列表、程序区分隔条与底部状态栏。
- 菜单、标签、输入、选择、滑条、对话框等本地交互；不会据此改变样例机床状态。

逐项范围、配置条件和与原生 AXIS 的差异见 [AXIS 功能对照](docs/axis-parity.md)。不包含外部 HAL 工具的内部界面、任意机床自定义面板、实际轨迹渲染或加工仿真。

## 架构约束

先读 [根目录 AGENT.md](../AGENT.md) 和 [前端 agent.md](agent.md)。按业务能力组织 `src/packages/<name>/`，模块内部拥有自己的组件、状态和实现；根文件是公开入口，子目录为私有。没有全局 `components/`、`stores/`、`api/` 分类层。

`app` / `pages` 负责启动与组合，业务模块之间通过明确的公开契约协调。状态归属、依赖方向和禁止导入的规则以 `agent.md` 与 `.dependency-cruiser.cjs` 为准；新增模块须同步更新这些规则。后续控制会话、协议、桌面适配各有独立边界，当前不创建空后端或伪控制链。

## 来源与许可证

前端代码标记为 `GPL-2.0-or-later`，参见仓库 [COPYING](../COPYING)。图标、样例程序和工具栏改绘的来源及不同许可证见 [资产说明](public/axis/NOTICE.md)。Web 保留独立的历史资源快照，不依赖原生 AXIS 的当前图标或生成工具。

## CI/CD

[Web CI](../.github/ci/README.md) 执行检查和构建，将 `dist/` 打包为带 commit 与校验和的静态产物，再通过浏览器测试验证同一份产物。发布只经过 [Web staging 安装器](../.github/staging/README.md)，不安装 LinuxCNC/AXIS 包。已有测试机需要按该文档更新一次安装器及 nginx；当前仓库变更不代表远端已迁移。
