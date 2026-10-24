# 简易与专业 Qt 界面

两套界面共享白金主题、同一个后端连接、程序文档及功能面板。默认进入专业模式；顶部“界面”可在简易/专业之间切换。模式与步骤是本次窗口的展示状态，当前不跨应用重启保存。

## 参考与取舍

- [QtDragon 官方说明与布局截图](https://www.linuxcnc.org/docs/html/gui/qtdragon.html)：参考其集中的手动控制、坐标、刀路与程序区组织方式。专业界面左侧常驻手动/MDI 与倍率，右侧上方刀路/坐标、下方程序，可拖动分隔条调整高度。
- [Bambu Studio 官方项目](https://github.com/bambulab/BambuStudio)及[窗口源码](https://github.com/bambulab/BambuStudio/blob/master/src/slic3r/GUI/MainFrame.cpp)：参考 Prepare / Preview / Device 的任务分页。简易界面适配为“准备程序 / 检查刀路 / 设备控制”，使用文字工具栏、状态卡片与下一步入口。

这是对 CNC 工作流的适配，没有复制这两个项目的源码、图标或商标，也没有接入 Bambu 云服务、切片、摄像头或材料去除引擎。准备页读取已有 G 代码；不会把 3D 打印机的温度、耗材或切片参数当作 CNC 参数。简易模式不降低服务端的操作限制，不根据卡片内容推断可以安全加工。

## 布局与复用

| 文件 | 所有权 |
| --- | --- |
| `qml/Workspace.qml` | 组合唯一的 ManualPanel、ToolpathPanel、ProgramPanel；持有展示状态与点动生命周期；将操作交给现有后端 |
| `qml/WorkspaceLayout.qml` | 布局输入和各面板矩形/可见性的公共契约，不接触机床状态 |
| `qml/ProfessionalLayout.qml` | 专业布局：左手动，右上刀路/坐标，右下程序 |
| `qml/GuidedLayout.qml` | 简易布局：准备、预览、设备三个步骤的面板几何与可见性 |
| `qml/WorkspaceGuide.qml` | 简易引导卡片，观察现有状态，调用公开 ChromeActions；底部操作固定，说明区可滚动 |
| `qml/BetterCnc/Chrome/ChromeBar.qml` | 共用菜单、模式切换、步骤导航；专业完整工具栏、简易文字工具栏；固定停止入口 |
| `qml/WorkspaceShortcuts.qml` | 共用快捷键；F3/F5 在简易模式定位到设备页，隐藏手动区不响应点动/回零快捷键 |

简易准备页在 1280 px 及以上同时显示程序、预览、引导卡片；窄窗口显示程序与引导卡片，预览在下一步显示。预览页显示大刀路区域和引导卡片。设备页显示刀路/坐标及完整手动控制，因此无需复制或简化机床规则。所有页面支持原有 760×640 最小窗口。

面板不通过 Loader 销毁重建，因此切换会保留 MDI 未提交文本、选中程序行、视角、单位、倍率反馈、选轴和点动步长。切换本身不提交加工命令；切换模式或步骤会取消当前点动手势并调用原有停止点动入口。程序运行状态继续来自后端，页面切换不会将运行解释为已完成。

## 操作与本地交互验收

生产界面在顶部选择“简易”或“专业”。原有 F1 急停、Esc 停止、F3 手动、F5 MDI 和菜单保留。简易工具栏的暂停按钮在后端报告 paused 后显示“继续”，并提交原有 `program.resume`。两套布局共享 `ChromeActions.canActivate` 与服务端能力限制。

无需 LinuxCNC 的交互窗口：

```sh
python.desktop/.venv/bin/python python.desktop/tests/visual_preview.py --interface guided
python.desktop/.venv/bin/python python.desktop/tests/visual_preview.py --interface professional
```

还可使用 `--stage preview`、`--stage device`、`--scenario offline` 或 `--scenario error`。这是明确标注“测试数据”的 FakeBackend，按钮记录请求，不控制硬件，也不自动模拟真实机床状态变化。两种模式的切换在同一个窗口内完成。

截图命令：

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
python.desktop/.venv/bin/python python.desktop/tests/visual_preview.py \
  --interface guided --stage preview --width 760 --height 640 --capture /tmp/guided.png
```

本地截图保存在忽略入库的 `python.desktop/artifacts/dual-ui/`。固定测试线段不代表实际 G 代码解释结果。

## 验证

使用 CMake/CTest 执行 QML UI、qmllint、模块边界、Python/后端集成及启动测试。新增交互回归覆盖：

- 模式切换保留 MDI 文本、程序选中行、刀路视角与步长，不提交额外命令。
- 简易步骤导航、隐藏手动区域拒绝方向键点动、离开设备页停止点动、F5 定位 MDI。
- 两套入口共用运行权限，离线/忙碌/后端拒绝时禁用；暂停、继续、停止提交原有命令。
- 760、1024、1280、1440 px 下三个简易步骤的面板互不重叠，停止与步骤入口可见，引导主操作不被滚动区域遮挡。
- 专业布局在相同宽度范围内保留程序分隔条与控制区。

macOS 无屏与本地窗口检查不能替代 Debian 13 / Intel 核显或真实机床验收。
