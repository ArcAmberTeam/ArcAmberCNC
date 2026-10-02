# 原生 Qt Quick 界面规范

先遵循根目录 [AGENT.md](../AGENT.md) 和 `$code-boundary-standards`。本目录是原生桌面入口，使用 C++17、CMake 和 Qt 6.8+；`frontend/` 保留为迁移对照与 Web 预览。不得把 Vue 页面嵌入 WebView 来代替 QML 迁移。

## 模块与公开入口

- `app/` 只拥有应用启动和 QML 引擎配置；`qml/Main.qml` 与 `qml/Workspace.qml` 组合窗口和功能模块，不拥有机床规则。
- `qml/BetterCnc/<Capability>/qmldir` 声明模块的公开类型；跨模块使用 `import BetterCnc.<Capability> 1.0`，不得使用相对路径、JavaScript 文件或 `internal` 类型绕过入口。
- `Ui` 拥有颜色、字体、图标绘制和通用控件；`Catalog` 拥有菜单/工具栏元数据、中文文案、固定样例及有出处的资源。两者不依赖功能模块，也不互相依赖。
- `Manual` 拥有手动/MDI、选轴和倍率；`Toolpath` 拥有静态预览、坐标数显及视图展示状态；`Program` 拥有只读程序列表、选中行及右键入口。三者只依赖 `Ui` 和 `Catalog`。
- `Chrome` 拥有菜单、工具栏和说明对话框，可依赖 `Ui`、`Catalog` 及 `ManualState`、`ToolpathState` 的公开展示接口，不导入其他功能模块的面板或私有类型。
- `Workspace` 组装功能面板、共享展示状态与快捷键。不得建立全局 `utils`、`stores`、`shared`、万能 action 分发器或机床状态桶。模块依赖必须无环。
- CMake 的资源列表、`qmldir` 与 `scripts/check_boundaries.py` 一起维护；新增模块先明确所有权及依赖，再更新检查，不通过忽略规则消除违规。

## 展示与系统边界

- 保持现有 Vue 的布局、颜色、字号、文案、动作 ID、快捷键、焦点与可编辑输入行为；大窗口、紧凑断点及最小窗口均须验收。
- `ManualState`、`ToolpathState` 和组件内属性只保存展示状态。坐标、主轴和运行状态仍为固定只读样例。
- 点动、运行、回零、急停、主轴、MDI 等仅触发“尚未连接控制器”的说明，不发送动作，不读取硬件，不自动启动 LinuxCNC 或 Python 服务。静态刀路是示意，不是解释器或加工仿真。
- 将来由独立 C++ 适配层拥有 Unix socket 和通用桌面接口，通过小而明确的 QObject API 交给 QML；组件不得直接访问平台、网络、文件、进程或 LinuxCNC。Python 保留机床规则与唯一命令写入所有权，LinuxCNC 保留实时职责。
- Qt 入口当前不调用现有 Tauri `health` 桥接；保留 Tauri/Rust 和 Python 诊断实现作为历史入口，不能将服务可达显示成机床已连接。
- 静态资源全部本地提供，保留许可证与出处，不加载 CDN、外部字体或遥测。大量真实刀路的解释和渲染另行设计，不塞入 QML 高频属性绑定。

## 验证与发布

- 修改后运行 CMake 配置/构建、`ctest --test-dir qt/build --output-on-failure` 及受影响 QML 的 `qmllint -I qt/qml`；测试使用公开模块和可观察 UI，不跨模块导入内部实现。
- 新建或修改依赖规则时，临时加入非法导入，确认失败，删除反例，再确认正常代码通过。
- 公共 UI 测试以 `objectName`、键盘和鼠标操作观察行为；不得为测试暴露私有实现或增添真实控制入口。
- macOS 构建和无屏测试不能替代 Debian 13、Intel 核显、中文字体、缩放与窗口生命周期验收。容器构建不表示目标机图形或机床已验证。
- `.github/workflows/ci.yml` 的原生 Qt job 调用 `scripts/ci-check.sh`，运行测试并生成独立 `.deb`；产物只上传，不自动安装或部署到机床。
- 构建、启动、打包及对照验收步骤见 [Qt 迁移说明](../docs/qt-qml-migration.md)。所有 README 仅由人工维护。
