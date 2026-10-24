# 在 LinuxCNC 主机接入新版 Qt 界面

目标链路是同一主机、同一用户下的 QML → DesktopBackend → Unix socket →
Python 控制服务 → LinuxCNC。SSH 仅用于维护，不参与机床命令传输。

## 已核实的目标环境

2026-10-25，通过 SSH 对 `teto@192.168.109.67` 做只读检查：

- 仓库：`/home/teto/ArcAmberCNC`；Debian 13，实时内核，Python 3.13.5，PySide6 6.8.2.1。
- 机床配置：`configs/zhulong-v2/烛龙V2.ini`；`DISPLAY = betterlinuxcnc`。
- 仓库根目录已有本机专用 `launcher.json`，包含机床 INI、CAM 地址与收件设置。
- 控制端点：`/run/user/1000/betterlinuxcnc/control.sock`。
- 当时运行的是 `/usr/bin/betterlinuxcnc-launch` 及 `/usr` 下安装的 GUI/服务。
- 公开 `machine.status` 返回 `connected: true`、`programState: idle`、
  `mode: manual`、`spindleSpeed: 0`。这只是查询时的状态，不是运动验收。

现有 GUI 后端已经支持真实 v2 控制会话，无需新增网络控制层。交互测试通过外部
注入接口替身；正式入口 `python.desktop/app/main.py` 和 `betterlinuxcnc` 不加载替身。

## 拉取后先检查连接

由用户自行 push/pull，不提交目标机专用 `launcher.json`、日志、密码或硬件配置副本。
目标机以 `teto` 用户执行：

```sh
cd ~/ArcAmberCNC
/usr/bin/python3 python.desktop/app/main.py --check-connection \
  --socket /run/user/1000/betterlinuxcnc/control.sock
```

这条命令只查询真实状态，不创建窗口、不附着控制会话、不续租点动，旧 GUI 可以继续连接。
输出 JSON；退出码 `0` 表示机床已连接，`2` 表示服务可达但机床未连接，`1` 表示
端点权限、传输或协议检查失败。使用 `--socket` 或 `BETTERCNC_SOCKET`，默认遵循
`XDG_RUNTIME_DIR`。不要配合 `--ini` 或 `--program` 使用；正式 GUI 附着时才校验 INI。

## 更新目标机正在使用的程序

仅 `git pull` 不会更新 `/usr/lib/betterlinuxcnc/python` 或
`/usr/share/betterlinuxcnc/qml`。原生 LinuxCNC 还会将系统程序目录放到 PATH 前面，
所以仅在 shell 中添加源码目录不能保证 DISPLAY 打开新版 GUI。
使用已有 CMake 安装入口同步 GUI、服务和启动器，无需重新编译 LinuxCNC 核心：

```sh
cd ~/ArcAmberCNC
cmake -S python.desktop -B python.desktop/build-target \
  -DBUILD_TESTING=OFF \
  -DCMAKE_INSTALL_PREFIX=/usr \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DBETTERCNC_PROJECT_DIR="$PWD" \
  -DPython3_EXECUTABLE=/usr/bin/python3
cmake --build python.desktop/build-target
```

以上仅在目标机准备安装文件。先由本机操作员完成正常停机、退出旧启动器与 LinuxCNC，
然后由用户执行安装及重新启动。不要在旧 GUI/控制服务仍使用文件时覆盖安装。

```sh
sudo cmake --install python.desktop/build-target
systemctl --user daemon-reload
betterlinuxcnc-launch --config "$HOME/ArcAmberCNC/launcher.json" --check
betterlinuxcnc-launch --config "$HOME/ArcAmberCNC/launcher.json"
```

`sudo` 仅用于安装，运行程序仍使用普通用户。安装更新 GUI、控制服务、CAM、启动器及已有
自动启动入口，不覆盖 `launcher.json`、机床 INI/HAL，也不安装 LinuxCNC 核心。
`--check` 只输出计划，不启动进程；不带 `--check` 的命令才会加载真实机床配置。
本文件中的安装/启动命令未通过 SSH 执行，需用户拉取后自行执行。

原有启动器按顺序启动控制服务、LinuxCNC（由其启动 DISPLAY），在读取到真实状态后启动 CAM。
GUI 和服务使用同一个 INI、同一个私有 socket；`session.attach` 拒绝配置不匹配或第二个控制界面。
原有 CAM 的 `auto_run` 设置不变。不要额外运行交互测试入口来连接真实机床。

## 单独启动界面

仅在核心和控制服务独立运行、没有其他 GUI 占用控制会话时使用：

```sh
cd ~/ArcAmberCNC
/usr/bin/python3 python.desktop/app/main.py \
  --ini "$HOME/ArcAmberCNC/configs/zhulong-v2/烛龙V2.ini" \
  --socket /run/user/1000/betterlinuxcnc/control.sock
```

这条命令直接加载仓库中的 GUI，不启动后端。不要关闭作为 DISPLAY 的旧界面后就假定
LinuxCNC 核心仍然运行；其退出会进入原生清理流程。

## 验收边界

新版本启动后，核对两种布局的坐标、轴数、回零标志、程序文本与实际机床状态。
程序加载、解释预览与加工运行应分别验收。断线不重放命令；服务只停止本会话点动并取消
未发送步骤，不自动中止已运行的程序。实际回零、点动、主轴、换刀和加工由本机操作员验收。
