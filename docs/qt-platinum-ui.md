# Qt 白金界面与组件结构

2026-10-24 按用户提供的《CNC白金视觉风格手册与AI重构规范》调整原生 QML 加工工作区。视觉采用暖白、香槟金、红色停止语义和白色面板；保留现有 LinuxCNC 控制协议、动作 ID、操作许可和点动生命周期。

## 文件职责

| 文件 | 职责 |
| --- | --- |
| `qml/BetterCnc/Ui/Theme.qml` | 集中颜色、字体、基本控件尺寸与间距；`accentFill` 为金色填充，`accent` 为可读的深金文字与焦点 |
| `qml/BetterCnc/Ui/Ui*.qml` | 公共按钮、输入、勾选、列表选择、滑块与图标的外观和焦点状态 |
| `qml/Main.qml` | 默认 1440×900 窗口、关闭及焦点生命周期 |
| `qml/Workspace.qml` | 宽窄布局、面板组合、后台反馈与点动按键所有权 |
| `qml/WorkspaceShortcuts.qml` | 非持续点动快捷键，显式注入展示状态与动作接口 |
| `qml/WorkspaceStatus.qml` | 底部持续可见的连接/操作状态与预览能力说明 |
| `qml/BetterCnc/Chrome/MachineStatus.qml` | 将真实快照映射为状态文字和颜色，不决定操作许可 |
| `qml/BetterCnc/Chrome/ChromeBar.qml` | 菜单与工具栏；停止按钮位于滚动区域之外 |
| `qml/BetterCnc/Manual/ManualPanel.qml` | 手动分组与点动手势、释放/失焦停止，组合内部控件 |
| `qml/BetterCnc/Manual/MdiControls.qml` | 内部 MDI 历史列表、输入和提交 |
| `qml/BetterCnc/Manual/OverrideControls.qml` | 内部倍率/速度控件，将用户修改上报给面板 |
| `qml/BetterCnc/Program/ProgramPanel.qml` | 程序文档、40 px 行高、选中行和执行行 |
| `qml/BetterCnc/Toolpath/ToolpathPanel.qml`、`ToolpathCanvas.qml` | 原有坐标与线段绘制，金色切削路径、蓝色空移虚线和窄窗口适配 |

`Manual` 的两个新控件在 `qmldir` 标记为 internal，其他模块仍通过 `ManualPanel` 使用。`MachineStatus` 为 Chrome 的公开展示类型。CMake 继续递归收集生产 QML 文件并整体安装；测试夹具位于 `tests/`，不进入安装目录。

## 布局与行为

- 当前支持简易/专业两套兼容界面，布局职责和交互说明见 [双界面说明](qt-dual-interface.md)。白金主题保持共用。
- 专业模式左侧手动控制，右侧刀路/坐标与程序上下分区；简易模式按准备、预览、设备分页。最小窗口仍为 760×640；设备面板为 304 px，紧凑窗口为 280 px，独立滚动。
- 顶部菜单与所有原有动作仍可访问。工具栏可横向滚动，停止按钮保持固定且带文字；急停与普通停止保持各自语义。
- 快捷键继续隔离可编辑输入、弹窗和菜单。持续点动按下/释放留在 Workspace 和 ManualPanel，未迁入快捷键展示组件。
- 状态显示由快照计算；断连优先于旧状态，未把空闲解释为加工完成，也没有生成加工百分比。

## 验证与本地预览

```sh
cmake --build python.desktop/build --parallel
ctest --test-dir python.desktop/build --output-on-failure
python.desktop/.venv/bin/python python.desktop/tests/visual_preview.py
```

最后一条打开明确标记“视觉验收 · 测试数据”的真实界面，使用 QML FakeBackend；按钮只记录请求，不连接服务或操作机床。可传 `--scenario offline` 或 `--scenario error` 查看断连与错误。

无屏截图示例：

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
python.desktop/.venv/bin/python python.desktop/tests/visual_preview.py \
  --width 1024 --height 768 --scenario offline --capture /tmp/cnc-offline.png
```

初版白金截图位于本机 `python.desktop/artifacts/platinum/`（忽略入库），双界面当前截图位于 `python.desktop/artifacts/dual-ui/`。截图中的几何是固定测试线段，不能作为真实 G 代码解释结果。

新增布局测试验证四个窗口尺寸下的面板不重叠、预览宽度、停止入口和状态条；新增状态测试覆盖断连、急停、加工中、暂停和结果未知。原有菜单、输入、点动、文件编辑、程序选择和 Python 公共接口测试仍运行。测试行选择改用控件定位，避免依赖旧主题的固定像素坐标。

## 与参考图的差异

当前应用是程序文本与刀路线段控制台，没有项目树、材料库、工艺编辑路由或材料去除引擎。因此左栏使用真实程序列表，中央明确称为刀路预览，不添加参考图中的虚构机型、工艺参数、模型实体或播放进度。

浮层采用规范允许的 `#FAF9F6` 实色回退，不引入背景模糊或新渲染依赖；状态和坐标立即更新，没有非必要动画。保留原有 Canvas 绘制架构。macOS 软件渲染与缩放截图不能替代 Debian 13 / Intel 核显目标机验收，也不证明机床操作已验收。
