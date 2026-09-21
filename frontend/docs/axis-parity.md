# AXIS 2.9.10 静态界面对照

本文件记录此 Web 原型的来源与覆盖范围。基准是本仓库 `VERSION` 中的 **2.9.10**，并非声称已覆盖所有 LinuxCNC 版本、所有 INI 配置或用户自定义 AXIS 界面。界面保留经典 Tk 布局，显示文案已按国内数控习惯本土化为简体中文；下方英文仅用于与历史源代码对照。

## 核对依据

| 本仓库来源                                                                                                                                                                       | 核对内容                                                                                                              |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| [`share/axis/tcl/axis.tcl`](https://github.com/Xamber-Software/BetterLinuxCNC/blob/e470d7aa6268a4ff56963cb8e162f2004ba89736/share/axis/tcl/axis.tcl)                             | 菜单 55–464、工具栏 489–780、Manual / MDI 及 Preview / DRO 788–1316、状态栏与程序区 1318–1376、倍率和速度控件 1380 起 |
| [`src/emc/usr_intf/axis/scripts/axis.py`](https://github.com/Xamber-Software/BetterLinuxCNC/blob/e470d7aa6268a4ff56963cb8e162f2004ba89736/src/emc/usr_intf/axis/scripts/axis.py) | 运行时菜单、轴与 joint、INI / HAL 条件显示、快捷键、工具与文件入口                                                    |
| [`docs/src/gui/axis.adoc`](../../docs/src/gui/axis.adoc)                                                                                                                         | AXIS 功能说明                                                                                                         |
| [`docs/src/gui/images/axis.png`](../../docs/src/gui/images/axis.png)                                                                                                             | 经典布局与颜色参考；图片标题显示 2.7.0-pre6，功能清单以本仓库 2.9.10 源码为准                                         |
| [`share/axis/images/`](https://github.com/Xamber-Software/BetterLinuxCNC/blob/e470d7aa6268a4ff56963cb8e162f2004ba89736/share/axis/images/)                                       | 删除前提交中的源码仅作历史参考；Web 工具栏快照及授权见 public/axis/NOTICE.md，原生改绘现已撤回                        |
| [`share/axis/images/axis.ngc`](https://github.com/Xamber-Software/BetterLinuxCNC/blob/e470d7aa6268a4ff56963cb8e162f2004ba89736/share/axis/images/axis.ngc)                       | 打包展示的 200 行 AXIS splash G-code                                                                                  |

以下“入口已展示”仅指标签、按钮和入口交互。涉及控制、磁盘、进程或外部程序的动作统一显示未实现说明，不执行对应操作。

## 菜单与工具栏

| 区域              | 对照入口                                                                                                                                                                                                             | 当前范围                                                                                              |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| File              | Open、Recent Files、Edit、Reload、Save G-code as、Properties、Edit tool data、Reload tool data、Ladder Editor、Quit                                                                                                  | 入口已展示；Recent Files 使用打包样例。文件选择和工具表只展示原型，不调用系统文件选择器、编辑器或写盘 |
| Machine / 程序    | Toggle Emergency Stop、Toggle Machine Power、Run program、Run from selected line、Step、Pause、Resume、Stop、Stop at M1、Skip lines with '/'                                                                         | 入口已展示；状态不会变成运行、已回零或已完成。M1 和跳行不发送控制设置                                 |
| Machine / MDI     | Clear MDI history、Copy from MDI history、Paste to MDI history                                                                                                                                                       | 入口已展示，不访问系统剪贴板或原生 MDI 历史文件                                                       |
| Machine / 工具    | Calibration、Show Hal Configuration、Hal Meter、Hal Scope、Show LinuxCNC Status、Set Debug Level                                                                                                                     | 入口已展示；这些外部工具的完整窗口不在本原型范围                                                      |
| Machine / 坐标    | Homing、Unhoming、Zero coordinate system（P1 G54 至 P9 G59.3，以及 G92）、Tool touch off to workpiece / fixture                                                                                                      | XYZ 样例子菜单和选择入口；无回零、偏置、刀补或 fixture 数据写入                                       |
| View / 方向和单位 | Top、Rotated Top、Side、Front、Perspective；Display Inches / MM                                                                                                                                                      | 可切换展示；投影为 SVG 仿射示意，不是三维相机或运动学计算                                             |
| View / 图层       | Show program、Show program rapids、Alpha-blend program、Show live plot、Show tool、Show extents、Grid、Show offsets、Show machine limits、Show velocity、Show distance to go、Large coordinate font、Clear live plot | 本地展示开关；图层和尺寸是样例。网格值不表示真实加工坐标或精度                                        |
| View / 状态显示   | Show commanded / actual position、Show machine / relative position、Joint / World mode、Show PyVCP panel                                                                                                             | 入口可见；反馈、坐标及 mode 为展示选项。PyVCP 无配置面板，仅说明入口                                  |
| Help              | About AXIS、Quick Reference                                                                                                                                                                                          | 展示来源及快捷键参考；内容做了 Web 静态原型说明，并非原生对话框逐像素拷贝                             |

普通铣床工具栏从左至右共 **19 个按钮**，分组顺序对应 Tcl：

1. Emergency Stop、Machine Power。
2. Open、Reload。
3. Run、Step、Pause / Resume、Stop。
4. Skip lines with '/'、Optional pause。
5. Zoom in、Zoom out、Top、Rotated top、Side、Front、Perspective、Drag / Rotate。
6. Clear live plot。

原始 Tcl 还定义第 20 个 **Inverted Front view**（`tool_axis_y2`），但 `axis.py` 在非车床配置下将其隐藏，本 XYZ 原型按普通铣床显示 19 个。暂停按钮的 `resume_inhibit` 变体已保留资产，未接入运行时 HAL 状态。

## 面板、状态与交互

| 区域           | 已呈现内容                                                                                        | 静态限制                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 外框           | 标题栏、菜单、工具栏、灰色面板、分隔条、底部三段状态                                              | 标题中的 STATIC PREVIEW 是刻意增加的说明；标题栏窗口按钮是装饰                     |
| Manual Control | XYZ 选择、点动 − / +、Continuous / 增量选择、Home All、Touch Off、Tool Touch Off、Override Limits | 可以选择和输入；机床动作只弹出说明。轴和 homed 标志不是硬件反馈                    |
| 主轴与冷却     | CCW / Stop / CW、转速 − / +、Brake、Mist、Flood                                                   | 均不控制输出；不通过点击模拟主轴或冷却状态                                         |
| 倍率与速度     | Feed Override、Rapid Override、Spindle Override、Jog Speed、Max Velocity                          | 滑条只改变本地展示值；范围来自原型样例，不代表已读取 INI 的配置上限                |
| MDI            | History、MDI Command、Go、Active G-Codes                                                          | 可选历史、编辑命令；Go 不执行、不排队，Active G-Codes 为固定样例                   |
| Preview        | 黑色背景、位置读数、坐标三轴、LinuxCNC 字样示意刀路、快速段、刀具、边界与尺寸                     | SVG 不是 G-code 解释结果，不具备圆弧/补偿/五轴姿态解析，不可用于碰撞或加工结果判断 |
| DRO            | XYZ 数字、速度、DTG、G54 / G92 / 刀长偏置和旋转读数                                               | 零值样例，不实现完整 LinuxCNC DRO 格式与所有配置组合                               |
| 程序区         | 原始 splash 程序、行号、选中行、滚动、Run from here 入口                                          | 只读；不执行、不显示真实执行行，不在预览中解析选中语句                             |
| 状态栏         | ESTOP、No tool、坐标及反馈显示模式                                                                | 固定样例状态与本地显示选项；不构成控制器状态报告                                   |

菜单、Tab、checkbox / radio 展示选项、输入框、滑条、行选择和分隔条属于本地 UI 行为。键盘参考会展示 AXIS 原生快捷键；参考中出现一个快捷键，不代表 Web 原型已经绑定相应机床动作。Reka UI 负责菜单及对话框的键盘焦点等通用交互。

## 配置条件与保留范围

原生 AXIS 会根据运行时配置增删控件，不能把所有 Tcl 定义同时出现的画面称为某台真实机床的默认界面。

| 条件                    | 原生 AXIS 行为与依据                                                                                                  | 本原型                                                          |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| 轴和 joint 数量         | `axis.py` 按 `axis_mask`、`num_joints` 显示 XYZABCUVW 与 joint 选择；非 identity 运动学区分 joint / world             | 固定 XYZ；不展示 A/B/C/U/V/W、多 joint 或龙门配对等机型         |
| 回零顺序                | `axis.py` 3535、3575 起：全部 joint 有 `HOME_SEQUENCE` 时才加入 Home All；非 identity 菜单使用 Joint 与 sequence 信息 | 按有回零顺序的 XYZ 样例展示 Home All 和单轴入口                 |
| Joint / World           | `axis.py` 4133 起：identity 运动学会移除这两个菜单项                                                                  | 为便于查看入口保留，本原型不是特定 identity INI 的完全复制      |
| 旋转轴速度              | `axis.py` 3793 起：没有 ABC 且没有 ANGULAR joint 时隐藏角度 Jog Speed                                                 | XYZ 样例不显示 `deg/min` 滑条                                   |
| 车床和后置刀架          | `axis.py` 4145 起：车床隐藏多种铣床视图和 rotate，使用 Y / Y2；非车床隐藏 Y2                                          | 未制作车床皮肤、半径/直径 DRO 或后置刀架界面                    |
| HAL 自动配置            | `axis.py` 4168 起：根据 HAL pin 连接隐藏 Brake、主轴、Spindle Override、Mist、Flood；限位开关决定 Override Limits     | 为检查入口而显示这些常用控件；没有 HAL 自动隐藏和运行时使能策略 |
| 网格和步距              | `DISPLAY.GRIDS` 可改网格；源码默认 `10mm 20mm 50mm 100mm 1in 2in 5in 10in`。`DISPLAY.INCREMENTS` 决定点动步距         | 不读取 INI；下拉内容为打包展示数据                              |
| 速度和倍率上限          | `DISPLAY` / `TRAJ` 中的速度与倍率配置决定原生滑条范围                                                                 | 固定样例范围；没有非线性原生速度映射或设备参数校验              |
| PyVCP、GladeVCP、嵌入页 | `axis.py` 3920 起由 INI 创建机床专属面板；未配置 PyVCP 时移除菜单项                                                   | 保留 PyVCP 说明入口；不生成或加载自定义控件、外部进程或嵌入程序 |
| Ladder / Tool Editor    | ClassicLadder 存在与运行状态影响菜单使能；工具编辑器由配置决定                                                        | 仅入口 / 占位对话框，不复制这些独立程序                         |
| 报警和状态使能          | Tcl 1720 起的状态表达式及 Python 通知面板随真实控制器状态更新                                                         | 不实现动态错误队列、进度、断点、resume-inhibit 或控制使能联锁   |
| 用户定制                | `USER_COMMAND_FILE`、`.axisrc`、Tk 扩展与机床 INI 可改变界面                                                          | 不运行用户 Python / Tcl，也不承诺复制任意定制界面               |

## 视觉与验收界限

当前工作复刻的是菜单结构、主要按钮、经典布局和控件风格。Tk、浏览器、Linux 字体、系统 DPI 与窗口管理器存在差异；未声明跨平台逐像素一致。SVG 示例、部分对话框和状态均有明确的静态简化。

工程检查命令见 [README](../README.md)。目标为 Debian 13 / Intel 核显，仍需在目标机确认字体、缩放、触控/鼠标、键盘、WebKitGTK 渲染与桌面宿主表现。浏览器构建或 Mac 上截图通过，不代表 LinuxCNC 控制接入、实时性能或目标设备验证通过。
