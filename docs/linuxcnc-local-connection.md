# LinuxCNC 专用机安装与维护

应用控制链路始终是同一主机、同一操作账户内的 QML → DesktopBackend → Unix socket → Python 控制服务 → LinuxCNC。SSH 只用于维护，不参与机床命令传输。

本文区分历史已验证环境与 `26.10.26.1` 的部署步骤。步骤存在不代表已在目标机执行；实际发布、迁移、登录策略和窗口检查应另记提交、版本及结果。当前本地及目标机均禁止构建、源码测试，包括本地 Docker；只由 GitHub CI 构建并发布完整 DEB，目标机只下载安装和验收运行状态。

## 历史已验证环境

2026-10-25，用户授权通过 `teto@192.168.109.67` 完成旧账户部署：

- 仓库 `/home/teto/ArcAmberCNC`，Debian 13、实时内核、Python 3.13.5、PySide6 6.8.2.1。
- 原机床配置 `configs/zhulong-v2/烛龙V2.ini` 使用 `DISPLAY = betterlinuxcnc`；仓库根 `launcher.json` 包含已有 INI、CAM 地址与收件设置。
- 当时 X11 为 `DISPLAY=:0`、`XAUTHORITY=/home/teto/.Xauthority`，控制端点 `/run/user/1000/betterlinuxcnc/control.sock`，实际 GUI 为 1024×600。
- 从 `origin/main` 的 `6a190df` 安装后，入口及 QML 摘要一致，用户服务报告 ready，GUI 能读取真实 LinuxCNC 状态；用户确认可用。
- 原 `launcher.json`、INI、VERSION/changelog 改动与未跟踪机床配置保留。未发送回零、点动、主轴、换刀或加工命令；当时读到的使能/急停状态不代表当前状态或运动验收。

这些历史 UID、Xauthority 和路径不能直接套用到新 `linuxcnc` 账户。

## 26.10.26.1 系统目录和账户

| 路径 | 内容及权限 |
| --- | --- |
| `/usr/bin/betterlinuxcnc*` | 应用 CLI，由包管理，root 所有 |
| `/usr/sbin/betterlinuxcnc-appliance` | 显式主机配置工具，管理操作要求 root |
| `/usr/lib/betterlinuxcnc`、`/usr/share/betterlinuxcnc` | 应用模块、维护工具、QML，普通用户不可写 |
| `/usr/lib/linuxcnc/modules/zhulong_homing.so` | 固定 HOMEMOD；仅通过匹配的 2.9.10 核心及头文件验证后显式启用 |
| `/usr/share/betterlinuxcnc/homing/provenance.json` | HOMEMOD 摘要、核心头文件摘要、源码提交和软件验证记录 |
| `/etc/betterlinuxcnc/launcher.json`、`machine/` | 迁移后的启动配置、INI/HAL 和相关配置副本，root 所有 |
| `/etc/betterlinuxcnc/updater.json` | 固定 root 更新配置，Debian conffile |
| `/usr/share/doc/betterlinuxcnc-qt/examples/launcher.example.json` | 示例；不覆盖现场配置 |
| `/var/lib/betterlinuxcnc/home` | `linuxcnc` 的 HOME，0700 |
| `/var/lib/betterlinuxcnc/{programs,inbox,machine}` | 程序、CAM 收件、可变刀具表/参数/位置，由 `linuxcnc` 写入 |
| `/var/cache/betterlinuxcnc/user` | `linuxcnc` 私有 XDG 缓存 |
| `/var/cache/betterlinuxcnc/update` | root 更新器私有缓存及安装日志 |
| `/var/lib/betterlinuxcnc/recovery/snapshots` | root 私有的配置/机床数据快照，保留最近 3 份 |
| `/var/log/betterlinuxcnc/launcher` | `linuxcnc:cnc-logs`，目录 2750；进程日志 0640 |
| `/run/user/<linuxcnc UID>/betterlinuxcnc/control.sock` | 本次登录的私有控制端点，不固定 UID |

`/var/lib/betterlinuxcnc`、`/var/cache/betterlinuxcnc` 和系统配置顶层保持 root 所有、不可被普通用户写入；不能递归将这些顶层交给 `linuxcnc`。启动器 `state.json`、socket 和锁保持私有，不随日志组共享。

`linuxcnc` 只运行专用 X11 全屏会话和应用，没有通用 sudo 或 SSH 登录权限。`cnc-maint` 只通过固定 SSH 命令读取诊断，不能登录桌面、获得 shell、上传文件或提权。系统 root 身份仍用于显式主机配置和受限更新服务，不提供日常 root SSH 登录。

## 发布包与安装前准备

产品版本是 `26.10.26.1`，Release 名称 `demo v26.10.26.1`，tag `v26.10.26.1`。正式 amd64 包为 `betterlinuxcnc-qt_26.10.26.1_amd64.deb`，同时发布 `SHA256SUMS`；必须为非 prerelease 的 latest Release。代码以 PR 合并到 main 并带 `build-release` 标签后，GitHub 验证同一提交的 CI 和包，再自动发布；完整约束见 [应用更新说明](firmware-updates.md)。

目标机只从已完成的 Release 下载 DEB 与校验文件，通过 apt/dpkg 安装；不拉源码构建，不安装 Rust/CMake 等构建工具。保留旧仓库的 `launcher.json`、机床目录及 VERSION/changelog 修改，供首次显式迁移审查；不使用 reset/clean 覆盖现场文件。GitHub 的源码 zip/tar 不能作为部署包。

安装或切换会话之前，重新只读检查机床状态，并由操作员完成正常停机。确认旧启动器、LinuxCNC 和控制服务已退出；不强杀核心，也不将“服务 active”当作机床空闲。原有 CAM `auto_run` 配置保留，连接验证不能随意上传测试程序。

以下操作只在已授权的目标机管理员环境进行。安装包的固定 postinst 自动 `provision` 专用账户和目录，不运行 `prepare`/`activate`、不创建机床副本、不写登录策略、不设置或重置密码。LightDM、Xorg 和 SSH 作为运行依赖安装，启用专用策略仍需显式执行。

```sh
cd /var/tmp/betterlinuxcnc-release-v26.10.26.1
sha256sum --check SHA256SUMS
dpkg-deb --field betterlinuxcnc-qt_26.10.26.1_amd64.deb Package Version Architecture
sudo apt-get install ./betterlinuxcnc-qt_26.10.26.1_amd64.deb
```

## 显式预演、准备与激活

先打开并保留可信的 root 维护会话，再执行迁移。激活会限制旧 `teto` 的 SSH 和 sudo；普通管理员 shell 不等于已取得的 root 会话。维护密码仅通过不回显的标准输入传入，不写进源码、环境变量、命令参数、包、脚本、日志或本文。

在保留的 root 会话中：

```sh
betterlinuxcnc-appliance plan
betterlinuxcnc-appliance stage \
  --source-config /home/teto/ArcAmberCNC/launcher.json \
  --destination /var/tmp/betterlinuxcnc-import-v26.10.26.1 \
  --zhulong-homing-travel-mm 420 275 90 --zhulong-xyz-only
```

`stage` 的目标目录必须尚不存在，只生成可审查副本，不改账户或系统登录策略。核对迁移后的 INI、HAL 引用、程序目录、刀具表、参数、位置文件和 CAM 收件目录。仅 G-code 程序扩展名被导入程序库；符号链接、特殊文件、INI include 与 CAM 私钥/令牌路径需要先单独审查。副本禁用外部编辑器和过滤器，原文件保持原样。

`420 275 90` 是用户于 2026-10-26 提供的 X/Y/Z 实测总行程，单位 mm；不可用于其他机床。此选项只将已审查的开关和回零配置合入现有机床副本，不用参考配置替换整套 INI。`stage` 标记安装验证待完成；正式 `prepare` 必须验证 `linuxcnc-uspace` 与 `linuxcnc-uspace-dev` 均为上游 2.9.10、已安装头文件摘要、HOMEMOD 来源及二进制摘要。缺少匹配的预编译开发包时停止，不能用 Debian 2.9.4 头文件或目标机构建绕过。

若只需接入开关，可在两条命令中改用互斥选项 `--zhulong-inputs-only`，保持 `motion.homing-inhibit=true`。不传这两项时保留原迁移语义。用户已确认本机实际仅有 XYZ，故上述命令同时指定 `--zhulong-xyz-only`，严格移除已审查的预留 ABC 配置和 HAL 连线，将实际 joint 数改为 3；主轴、其他 IO 和板卡六路 stepgen 能力保留。若不指定此选项，仍保留 ABC 的真实回零联锁；不得用伪造 homed 绕过。本工具不触发 HOME 或其他运动。

本次回零后的软限位为 X 0～410、Y −265～0、Z 0～80 mm；两端各留 5 mm。已有参数与刀具表保留，现场首次回零后必须核对工件坐标（如 G54）和刀长，旧坐标不能当作已验证可直接加工。

审核后首次准备：

```sh
betterlinuxcnc-appliance prepare \
  --source-config /home/teto/ArcAmberCNC/launcher.json \
  --zhulong-homing-travel-mm 420 275 90 --zhulong-xyz-only
systemd-ask-password '设置专用维护账户密码' | betterlinuxcnc-appliance set-maintenance-password
runuser -u linuxcnc -- env HOME=/var/lib/betterlinuxcnc/home \
  XDG_CACHE_HOME=/var/cache/betterlinuxcnc/user \
  /usr/bin/betterlinuxcnc-launch --config /etc/betterlinuxcnc/launcher.json --check
```

安装包已幂等准备账户与目录；`prepare` 显式复制配置和运行数据，不覆盖已存在的专用机配置，也不启动 LinuxCNC。已完成迁移的机器不在普通升级时重复执行；重复安装和更新不会重设维护密码。`--check` 只检查配置、依赖及启动计划，不证明硬件或控制连接正常。

确认准备结果后显式激活：

```sh
betterlinuxcnc-appliance activate
/usr/sbin/sshd -t
/usr/sbin/sshd -T
/usr/sbin/visudo -c
```

激活将固定 LightDM/X11/logind、SSH、sudo、Polkit 与 SysRq 策略写入系统。SSH 由工具管理完整 `/etc/ssh/sshd_config`，不依赖可被其他 Include/Match 覆盖的 drop-in；sudo 主配置仅保留 root 规则，不再通过旧授权授予普通账户 sudo。旧策略内容、权限及恢复记录存入 root 私有的 `/var/lib/betterlinuxcnc/recovery/<时间>/policies.json`。

`activate` 仅启用无写卡权限的 Mesa 自动检查 timer，不重载 SSH、重启图形会话或重启主机。先检查 `sshd -T` 的有效配置与 `visudo` 结果，再由保留的 root 会话按部署窗口重载 SSH，验证新的 `cnc-maint` 连接。LightDM、X11、logind 和内核策略在受控重启后验收；必须确认机床已停机，并保留现场恢复途径。全部验证完成前不要关闭既有 root 会话。没有通用 SSH 管理 shell 时，策略恢复由受控本机管理员处理，不通过维护命令绕过限制。

## 专用会话与只读连接验收

LightDM 自动登录 `linuxcnc`，选择 `betterlinuxcnc-kiosk` X11 会话。该会话运行 `betterlinuxcnc-launch --kiosk-session`，导入实际 DISPLAY/Xauthority 后启动 `betterlinuxcnc-launcher.service` 用户服务，并持续维持会话；等待或启动失败时显示不连接机床的独立状态页，不退回普通桌面或登录选择器。不要再手动并行启动第二套 launcher。

在已登录的目标机 root 维护会话中，按实际 UID 做只读核查：

```sh
operator_uid=$(id -u linuxcnc)
runuser -u linuxcnc -- env XDG_RUNTIME_DIR="/run/user/$operator_uid" \
  DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$operator_uid/bus" \
  /usr/bin/systemctl --user status betterlinuxcnc-launcher.service --no-pager -l
runuser -u linuxcnc -- env XDG_RUNTIME_DIR="/run/user/$operator_uid" \
  /usr/bin/betterlinuxcnc --check-connection \
  --socket "/run/user/$operator_uid/betterlinuxcnc/control.sock"
dpkg-query -W -f='${Package} ${Version}\n' betterlinuxcnc-qt
```

`--check-connection` 只发送 `machine.status`，不附着控制会话、不续租点动；不要与 `--ini` 或 `--program` 合用。退出码 0 为机床已连接，2 为服务可达但核心未连接，1 为端点/权限/协议错误。只有已建立真实图形用户会话时才能使用其用户 bus；不要以自建临时 bus 冒充正式会话。

共同检查：实际全屏窗口和触控、当前账户、无普通桌面/终端入口、本次日志目录的私有 `state.json` ready、真实状态及 QML/Python 安装版本。进程日志在 `/var/log/betterlinuxcnc/launcher/<本次启动目录>/`；不要沿用历史 PID、截图或 `~/.local/state` 路径。应用界面文件选择限定程序库和收件目录，不能作为主机文件浏览器。

## 固定 SSH 维护接口

专用策略生效后，仅允许 `cnc-maint@192.168.109.67`，且每次只接受一个无参数命令：

```sh
ssh cnc-maint@192.168.109.67 help
ssh cnc-maint@192.168.109.67 version
ssh cnc-maint@192.168.109.67 status
ssh cnc-maint@192.168.109.67 logs
ssh cnc-maint@192.168.109.67 diagnostics
```

`help` 列出允许命令；`version` 查询应用/核心包版本；`status` 查看 LightDM 和固定更新系统单元；`logs` 只返回最近三个运行目录内规定的进程日志尾部；`diagnostics` 返回固定的内核、存储和 `linuxcnc` 进程信息。没有任意路径参数，不提供文件编辑、上传/SFTP/SCP、TTY、端口转发、X11 转发或 sudo。任意 shell 命令和额外参数必须被拒绝。

维护 `status` 不读取控制 socket，不能证明机床空闲。未来常规升级由 GUI 请求固定 root 更新服务，维护账户不负责拉取源码、构建或安装包。

## 更新前备份与人工恢复边界

root 更新服务在正常停止启动器、确认控制 socket 和原生锁已消失后，先执行固定 `betterlinuxcnc-appliance backup`，成功后才调用 apt 安装。备份失败会阻止安装并显示错误，控制系统保持停止；不会跳过备份或自动恢复旧内容。

需要单独备份时，先正常停机，在保留的可信 root 维护会话中运行：

```sh
betterlinuxcnc-appliance backup
```

命令不接受任意路径，快照固定保存在 `/var/lib/betterlinuxcnc/recovery/snapshots`，只有 root 可访问。范围为 `/etc/betterlinuxcnc`、`/var/lib/betterlinuxcnc/machine` 的参数/刀具表/位置等可变数据，以及工具管理的 LightDM、X11、logind、SSH、sudo、Polkit 和 SysRq 固定策略文件；清单记录 SHA-256、应用版本与创建时间。只有新快照创建并校验成功后才清理旧快照，保留最近 3 份。

快照不包含大型程序库、CAM 收件、日志、缓存、账户密码或 SSH 私钥，也不包含整个系统镜像。它与 `activate` 保存的原登录策略清单用途不同，不会自动导入或恢复任何配置。恢复需由受控管理员先核对版本、摘要及现场状态，再决定具体恢复内容；`cnc-maint` 的固定维护命令不提供备份下载或恢复入口。

这些快照与原数据位于同一块系统盘，不能防止磁盘损坏或整盘丢失。需要保留的程序、凭据及异盘备份应由现场另行管理；本功能不表示已完成灾难恢复或机床验收。

## 验收记录边界

### 2026-10-26 三轴开关只读实测

用户手动按压开关，通过已运行系统的 `halcmd getp` 只读采样，约每 100 ms 查询一次；未修改目标机文件、HAL 连线或机床使能，未发送运动命令。开始时原生状态为急停且未使能。

| 用户确认的物理轴 | 原始输入 | 松开 | 按下 | 观察到的保持时间 |
| --- | --- | --- | --- | --- |
| X | `hm2_7i92.0.gpio.020.in` | FALSE | TRUE | 两次约 1.34/1.44 秒，最后一次约 6.91 秒 |
| Y | `hm2_7i92.0.gpio.021.in` | FALSE | TRUE | 连续六次约 1.34～2.79 秒 |
| Z | `hm2_7i92.0.gpio.022.in` | FALSE | TRUE | 两次约 1.03/1.96 秒 |

三路在保持期间的采样均无中途跳变，释放后恢复 FALSE；同时捕捉到快速点按响应。用户分别确认 Y、最后一次 X 和此前两次 Z 的物理轴标识。这支持此目标机使用 `.in` 作为有效高触发源；100 ms 采样不能测量更短的机械抖动，也不能替代防抖验证。

当时旧配置的 `joint.0/1/2.home-sw-in` 以及 X 负/Y 正/Z 负限位仍为 FALSE，信号没有 GPIO 写入源。因此开关采样仅验证开关到板卡的输入及映射，未验证 LinuxCNC 限位响应或回零运动。用户随后另行提供 X/Y/Z 总行程 420/275/90 mm，作为完整配置迁移的输入。接线与回零模块仍须通过 PR/CI/Release 后部署，行程输入和软件测试都不等于现场运动验收。

分别记录发布提交与包摘要、安装版本、配置/数据保留、账户和文件权限、SSH 正负访问结果、专用会话、日志和只读控制连接。两种 UI 布局的坐标、轴数、回零标志、程序文本应与实际状态一致。

软件包、登录隔离和只读状态通过，不代表已完成回零、点动、主轴、换刀或加工验收。程序加载、解释预览与加工运行须分别验收；实际机床动作由本机操作员确认。断线不重放命令，服务只停止本会话点动并取消未发送步骤，不自动中止已运行的程序。
