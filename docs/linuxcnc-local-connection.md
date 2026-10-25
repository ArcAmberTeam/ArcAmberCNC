# 在 LinuxCNC 主机接入新版 Qt 界面

目标链路是同一主机、同一用户下的 QML → DesktopBackend → Unix socket →
Python 控制服务 → LinuxCNC。SSH 仅用于维护，不参与机床命令传输。

## 已核实的目标环境

2026-10-25，通过 SSH 检查 `teto@192.168.109.67`，随后经用户授权完成构建、安装和启动：

- 仓库：`/home/teto/ArcAmberCNC`；Debian 13，实时内核，Python 3.13.5，PySide6 6.8.2.1。
- 机床配置：`configs/zhulong-v2/烛龙V2.ini`；`DISPLAY = betterlinuxcnc`。
- 仓库根目录已有本机专用 `launcher.json`，包含机床 INI、CAM 地址与收件设置。
- 控制端点：`/run/user/1000/betterlinuxcnc/control.sock`。
- 图形会话：X11 `DISPLAY=:0`，`XAUTHORITY=/home/teto/.Xauthority`；实际 GUI 窗口为 1024×600。
- 已从合并后的 `origin/main` 提交 `6a190df` 安装 GUI、控制服务和启动器；安装后的 GUI Python 入口与 Main.qml 均与仓库文件摘要一致。
- `betterlinuxcnc-launcher.service` 用户服务已启动，启动器报告 `ready`；GUI、真实 LinuxCNC、控制服务及 CAM 进程正常运行，用户确认可用。
- 启动后只读反馈为已连接、急停且未使能；最后一次查询为手动、空闲、已使能、主轴转速 0。本次 Agent 未发送上电、回零、点动、主轴或加工命令；这些状态只是当时的反馈，不是运动验收或当前状态保证。
- 安装前后 `launcher.json` 和机床 INI 摘要相同；原有 VERSION、debian/changelog 修改与未跟踪机床配置目录保留。

现有 GUI 后端已经支持真实 v2 控制会话，无需新增网络控制层。交互测试通过外部
注入接口替身；正式入口 `app/desktop/app/main.py` 和 `betterlinuxcnc` 不加载替身。

## 拉取后先检查连接

源码在本地修改、验证后推送，目标机从 Git 同步。用户已授权 Agent 使用 GitHub Desktop
推送及在目标机拉取、构建、安装和启动。不提交目标机专用 `launcher.json`、日志、密码或硬件配置副本。
每次核对工作分支和 HEAD，不能只看 `origin/main`：本次曾发现远端引用已更新，而工作分支仍在旧提交。
确认目标引用后可使用 `git merge --ff-only origin/main`；若无法快进，先检查分歧，不用强制重置覆盖现场修改。

目标机以 `teto` 用户执行只读连接检查：

```sh
cd ~/ArcAmberCNC
/usr/bin/python3 app/desktop/app/main.py --check-connection \
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
cmake -S . -B build-target \
  -DBUILD_TESTING=OFF \
  -DCMAKE_INSTALL_PREFIX=/usr \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DBETTERCNC_PROJECT_DIR="$PWD" \
  -DPython3_EXECUTABLE=/usr/bin/python3
cmake --build build-target
```

以上仅在目标机准备安装文件。先确认机床已按正常流程停机，旧启动器、LinuxCNC 与控制服务均已退出，
再执行安装及重新启动。不要在旧 GUI/控制服务仍使用文件时覆盖安装，也不要以强杀进程代替正常停机。

```sh
sudo cmake --install build-target
systemctl --user daemon-reload
betterlinuxcnc-launch --config "$HOME/ArcAmberCNC/launcher.json" --check
export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"
xdpyinfo >/dev/null
systemctl --user import-environment DISPLAY XAUTHORITY
systemctl --user start betterlinuxcnc-launcher.service
```

`sudo` 仅用于安装，运行程序仍使用普通用户。安装更新 GUI、控制服务、CAM、启动器及已有
自动启动入口，不覆盖 `launcher.json`、机床 INI/HAL，也不安装 LinuxCNC 核心。
`--check` 只输出计划，不启动进程；启动用户服务才会加载真实机床配置。
systemd 启动流程已在目标机实际执行；上述构建命令已更新为目录整理后的根 CMake 入口，新目录版本仍需随实际部署另行验收。用户服务独立于 SSH 会话，断开 SSH 后继续运行。
需要直接在图形终端运行时，也可使用 `betterlinuxcnc-launch --config ./launcher.json`，但不能与用户服务并行启动。

原有启动器按顺序启动控制服务、LinuxCNC（由其启动 DISPLAY），在读取到真实状态后启动 CAM。
GUI 和服务使用同一个 INI、同一个私有 socket；`session.attach` 拒绝配置不匹配或第二个控制界面。
原有 CAM 的 `auto_run` 设置不变。不要额外运行交互测试入口来连接真实机床。

## 启动后检查

```sh
systemctl --user status betterlinuxcnc-launcher.service --no-pager -l
betterlinuxcnc --check-connection --socket /run/user/1000/betterlinuxcnc/control.sock
journalctl --user -u betterlinuxcnc-launcher.service -n 30 --no-pager
ls -lt "$HOME/.local/state/betterlinuxcnc/launcher"
```

systemd 的 active 只代表启动器仍在运行；继续读取本次启动目录的 `state.json` 和
`controller-*.log`、`linuxcnc-*.log`、`cam-link-*.log`，确认 ready、真实状态可读和窗口显示。
直接 CLI 启动的默认日志目录为项目 `.runtime/launcher/`，不要与用户服务日志混淆。
需要核对安装内容时，比较仓库和 `/usr/lib/betterlinuxcnc/python`、
`/usr/share/betterlinuxcnc/qml` 中对应文件的摘要。记录当前提交和检查结果，不沿用旧截图或 PID。

## 单独启动界面

仅在核心和控制服务独立运行、没有其他 GUI 占用控制会话时使用：

```sh
cd ~/ArcAmberCNC
/usr/bin/python3 app/desktop/app/main.py \
  --ini "$HOME/ArcAmberCNC/configs/zhulong-v2/烛龙V2.ini" \
  --socket /run/user/1000/betterlinuxcnc/control.sock
```

这条命令直接加载仓库中的 GUI，不启动后端。不要关闭作为 DISPLAY 的旧界面后就假定
LinuxCNC 核心仍然运行；其退出会进入原生清理流程。

## 验收边界

新版本启动后，核对两种布局的坐标、轴数、回零标志、程序文本与实际机床状态。
程序加载、解释预览与加工运行应分别验收。断线不重放命令；服务只停止本会话点动并取消
未发送步骤，不自动中止已运行的程序。实际回零、点动、主轴、换刀和加工由本机操作员验收。
