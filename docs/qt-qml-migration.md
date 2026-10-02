# Vue 到原生 Qt Quick/QML 的迁移

决策日期：2026-10-02。将当前 Vue 页面按已有布局、资源、文案和交互迁移到原生 Qt Quick/QML，新增正式桌面入口 `qt/`。`frontend/` 继续提供迁移对照与 Web 预览，Tauri 桌面环境、Rust 诊断桥和 Python 本地服务保留，不在这次迁移中删除。原 Tauri 唯一入口决策由本文取代，历史设计保留在 [Tauri 架构记录](tauri-local-control-architecture.md)。

本次迁移覆盖当前界面原型：菜单、工具栏、手动/MDI、坐标数显、静态刀路、程序列表、说明对话框、快捷键、倍率滑条与面板缩放。点动、回零、急停、主轴、运行和 MDI 执行仍只显示“尚未连接控制器”的说明。固定坐标与刀路不是硬件反馈，也不是解释器输出。Qt 入口不发送机床命令，不读取硬件，不自动启动 Python 或 LinuxCNC。

## 模块与数据边界

工程使用 Qt 6.8+、C++17、CMake 和 Qt Quick Controls Basic。C++ 启动应用并加载嵌入资源的 QML；页面使用原生控件和绘制，不嵌入浏览器。QML 模块通过 `qmldir` 公开类型、命名导入和信号协作。

| 所有者                              | 职责                                            | 允许依赖                                |
| ----------------------------------- | ----------------------------------------------- | --------------------------------------- |
| `app/`、`Main.qml`、`Workspace.qml` | 启动、窗口、布局、快捷键与模块组合              | 功能模块的公开入口                      |
| `BetterCnc.Ui`                      | Theme、字体、图标绘制、通用控件                 | Qt 模块                                 |
| `BetterCnc.Catalog`                 | 菜单/工具栏元数据、中文文案、固定演示数据和资源 | Qt 模块                                 |
| `BetterCnc.Manual`                  | 手动/MDI、选轴、倍率及 `ManualState`            | Ui、Catalog                             |
| `BetterCnc.Toolpath`                | 静态刀路、DRO、缩放和 `ToolpathState`           | Ui、Catalog                             |
| `BetterCnc.Program`                 | 只读程序、选中行、右键入口                      | Ui、Catalog                             |
| `BetterCnc.Chrome`                  | 菜单、工具栏、说明对话框                        | Ui、Catalog、ManualState、ToolpathState |

Ui 与 Catalog 没有业务模块依赖。功能模块不得相互导入面板或私有实现，内部类型使用 `qmldir` 的 `internal` 声明。`scripts/check_boundaries.py` 检查模块入口和依赖；功能规则见 [Qt AGENTS](../qt/AGENTS.md)。

后续控制链路规划为 `QML → 独立 C++ 会话/平台适配层 → Unix domain socket → Python 控制服务 → LinuxCNC`。Qt 适配层拥有通信、窗口和文件等外部接口，通过窄 QObject 接口提供只读状态和明确操作；QML 控件不直接访问 socket 或设备。Python 继续拥有机床规则、命令写入口与错误读取入口，LinuxCNC 继续负责实时控制。该适配层与真实控制当前尚未实现，不能把展示属性当成控制器状态。

## macOS 本机配置、构建与打包

需要已安装的 Qt 6.8+，包含 Quick、QuickControls2、Svg 和 QuickTest，以及 CMake、Ninja 和 Python 3。以下命令从仓库根目录执行；`qt_prefix` 指向实际 Qt 安装，本次开发机使用 `~/Qt/current/macos`。

```sh
qt_prefix="$HOME/Qt/current/macos"
cmake -S qt -B qt/build -G Ninja \
  -DCMAKE_PREFIX_PATH="$qt_prefix" -DCMAKE_BUILD_TYPE=Release
cmake --build qt/build --parallel
ctest --test-dir qt/build --output-on-failure
open qt/build/betterlinuxcnc.app
```

Qt 的 `macdeployqt` 可将依赖与 QML 导入部署进应用包；`-qmldir` 指向应用源码，以便扫描 QML 依赖。详见 [Qt 官方 macOS 部署文档](https://doc.qt.io/qt-6/macos-deployment.html)。

```sh
"$qt_prefix/bin/macdeployqt" qt/build/betterlinuxcnc.app \
  -qmldir="$PWD/qt/qml" -always-overwrite
```

发布给其他 Mac 前另行完成签名、公证与干净机器启动检查；当前命令只处理 Qt 依赖部署。需要镜像文件时可以按 `macdeployqt -help` 增加 `-dmg`。

## Debian 13 构建、运行与软件包

Debian 13 trixie 的 [Qt Declarative 开发工具](https://packages.debian.org/trixie/qt6-declarative-dev-tools) 和 [Qt Quick Controls 模块](https://packages.debian.org/trixie/qml6-module-qtquick-controls) 提供 Qt 6.8.2，满足工程最低版本。开发依赖和所有运行/测试 QML 模块集中列在 [`qt/scripts/ci-check.sh`](../qt/scripts/ci-check.sh)，包含 CMake、Ninja、C++ 编译器、Qt Base/Declarative/Svg、QtTest QML 模块、Python、Noto CJK 和 Liberation 字体。等宽字体依照原 Web 的字体顺序选取 SFMono-Regular、Consolas、Liberation Mono，并以 Courier New 回退。

在一次性 Debian 13 容器中复现 CI：

```sh
docker run --rm --init --platform linux/amd64 \
  --mount "type=bind,src=$PWD,dst=/workspace" \
  --workdir /workspace \
  debian:13-slim \
  bash qt/scripts/ci-check.sh --install-deps
```

`--install-deps` 仅用于有 root 权限的一次性容器。已有依赖的 Debian 开发环境可执行 `bash qt/scripts/ci-check.sh`；该脚本构建、运行 CTest、生成 `.deb` 并检查包内容，再提取软件包、无屏启动其中的二进制 3 秒，确认嵌入 QML 正常加载。不要复用由 macOS 或其他 Qt 安装生成的同一个 `qt/build` CMake 缓存；不同平台使用各自的工作副本。

等效构建和打包步骤为：

```sh
cmake -S qt -B qt/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
cmake --build qt/build --parallel
ctest --test-dir qt/build --output-on-failure
(cd qt/build && cpack -G DEB)
```

在具有桌面会话的 Debian 13 机器安装已验证的软件包后，通过应用菜单或 `betterlinuxcnc` 启动。软件包依赖由 CPack 的共享库检测和显式 QML 运行模块共同声明；软件包不安装、启动或配置 LinuxCNC/Python 控制服务。CI 的 offscreen/software 设置只用于无屏测试，正常运行使用目标机器的图形环境。

## QML 源码验证与对照验收

CMake 的 CTest 入口运行公共 UI Qt Quick Test、模块边界检查和零警告 qmllint。Qt Quick Test 从源码目录加载 QML，通过公开组件、可观察状态与 UI 操作验收，避免跨模块引用私有实现；测试无需构建后的真实控制服务。

安装 Qt 工具后，也可从仓库根目录直接执行源码检查和 UI 测试：

```sh
python3 qt/scripts/check_boundaries.py
find qt/qml -name '*.qml' -exec qmllint --max-warnings 0 -I qt/qml {} +
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QT_QUICK_CONTROLS_STYLE=Basic \
  qmltestrunner -import "$PWD/qt/qml" -input qt/tests
```

若 Debian 的 Qt 工具未在 PATH 中，使用 `/usr/lib/qt6/bin/qmllint` 与 `/usr/lib/qt6/bin/qmltestrunner`；macOS 可使用 `$qt_prefix/bin/` 中的对应工具。

视觉与交互对照至少包含：常规窗口、900px 紧凑断点、760×640 最小窗口、拖动/键盘调整程序区、整列滚动、菜单及子菜单、F3/F5 与视图快捷键、MDI 输入焦点、轴选择、Preview/DRO、显示开关、程序行与右键菜单、各说明对话框。两种渲染栈的字体、字距、抗锯齿与设备缩放需要在相同平台、字体和缩放下逐项对照，不能仅凭本机截图声称所有环境像素完全相同。

## CI 与验收状态

既有 `.github/workflows/ci.yml` 增加 `qt-build`，在 GitHub 托管 `ubuntu-24.04` 上启动 Debian 13 容器，执行原生构建、CTest 和 CPack；成功后上传 `betterlinuxcnc-qt-debian13`，失败时保存 CTest 诊断。该 job 纳入原有 `CI Gate`，不新增独立工作流，不改变 Web 分支部署规则，Qt `.deb` 不自动安装到机床。

本文描述实现边界和复现方法，不作为 Debian CI 已通过的证据。实际验证结果以对应提交的命令输出和 CI 记录为准。macOS 构建、无屏 UI 测试、Debian 容器打包分别不能替代 Debian 13 Intel 核显上的图形/字体/缩放验收，也不表示真实机床控制已经接入。
