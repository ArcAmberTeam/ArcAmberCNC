# 无 LinuxCNC 的 GUI 回归测试

GUI 测试使用 Qt Quick Test 加载真实 QML 窗口，并注入 `app/desktop/tests/FakeBackend.qml`。该替身提供确定的状态快照、程序文本和请求记录，不连接 socket、不启动 LinuxCNC 或模拟器，也不会执行机床操作。生产启动器不加载该替身。

## 交互式手动测试

在仓库根目录执行：

```sh
app/desktop/.venv/bin/python app/desktop/tests/interactive/main.py
```

同时打开标有“交互测试”的真实 GUI 和独立测试控制台。此入口只需 PySide6，不需要先编译 C++ 测试启动器。关闭任一窗口会退出整套交互测试。

1. 在真实界面点击运行、主轴、冷却，或按住/松开点动按钮；控制台下方显示请求 ID 和参数，状态区显示停止点动调用计数。
2. 在控制台选择“断开”“未上电”“急停”“运行中”“暂停”“就绪”，观察真实界面的禁用条件和显示状态。操作请求不会自动修改快照，反馈由控制台独立注入。
3. 拖动 X/Y/Z 滑块观察坐标和实际轨迹，修改执行行观察程序区滚动和高亮；在程序列表点击行观察对应刀路线段。
4. 点击“操作报错”或“预览失败”观察错误展示；点击“加载示例”恢复矩形示例刀路，“重置测试”恢复初始测试状态。

所有坐标、程序与刀路均为显式测试数据，矩形刀路没有经过 G 代码解释器。打开和保存文件只记录请求，不读取或写入磁盘。MDI 不执行；点动不会自动改变坐标。控制台保留最近 100 条请求，并可清空。生产入口与安装产物不包含此测试入口。

## 本机运行

需要 Qt 6.8+ 的 Quick、QuickControls2、QuickTest 开发组件、CMake、C++17 编译器；Python 后端及启动检查还需要 Python 3.11+ 和 PySide6。

从仓库根目录运行，按本机安装位置调整 Qt 和 Python 路径：

```sh
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$HOME/Qt/6.12.0/macos" \
  -DPython3_EXECUTABLE="$PWD/app/desktop/.venv/bin/python"
cmake --build build --parallel
ctest --test-dir build -R '^qml-ui$' --output-on-failure
```

CTest 自动设置 `QT_QPA_PLATFORM=offscreen`、`QT_QUICK_BACKEND=software` 和 Basic 控件样式，不需要手动打开 GUI 或运行控制服务。

同时检查模块边界、生产 QML 静态检查、Python 公共接口和离线启动：

```sh
ctest --test-dir build \
  -R '^(qml-ui|module-boundaries|qml-lint|python-integration|desktop-startup)$' \
  --output-on-failure
```

Python 公共接口测试使用临时 Unix socket 和受控服务替身，需要运行环境允许创建本地 socket。macOS 沙箱若限制图形服务或 socket，应在普通本机终端执行。

## 覆盖范围

- `tst_workspace.qml`：点动按下/释放、焦点与模式变化、离线禁用、MDI、倍率、对刀及窗口布局。
- `tst_chrome.qml`：菜单、工具栏、快捷键、弹窗、编辑草稿及异步失败反馈。
- `tst_panels.qml`：程序行选择、坐标转换、预览图层及小窗口显示。

新增的 13 个工作区场景覆盖：

- 断连、未上电、急停、忙碌、自动模式、没有可用轴、能力被禁用时，鼠标及键盘均不发送点动请求（7 个场景）。
- 按住点动期间断线，重连及松键不重放旧命令；重新按键才发出新请求。
- 离线仍可缩放、切换视角和预览/数显页签，且不发送控制命令。
- 对刀输入为空、空白、非数字或溢出时保留弹窗并显示错误；纠正为有效值后才提交（4 个场景）。

这些测试验证界面行为与命令意图，不验证真实 LinuxCNC 执行、机床运动或硬件安全。解释器预览使用测试数据，不代表真实 G 代码解释结果。
