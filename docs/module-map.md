# 模块职责与目录地图

2026-10-25：自有应用统一放在 `app/`，按职责命名；HAL 和设备驱动回到 `src/hal/` 的上游实体路径。实现语言由模块构建清单声明。Python 包名、Rust crate 名、控制协议与已安装命令保持兼容，根规范见 [AGENT.md](../AGENT.md)。

## 源码所有者

```text
CMakeLists.txt               产品应用构建、测试、安装与打包的组合入口
cmake/ApplicationInstall.cmake 默认 /usr、lib 安装布局
app/
  desktop/                   PySide6 + QML 桌面
    app/                     GUI 启动
    python/bettercnc/         desktop 适配与 session Unix 客户端
    qml/BetterCnc/            Ui、Catalog、Manual、Toolpath、Program、Chrome
    tests/                   QML 公共界面和 Python 公共接口测试
  controller/                Python 控制服务、机床规则与隔离解释预览
    src/                     service、controller、preview 公开包
    tests/                   控制、协议、文件与预览验证
  cam-link/                  Rust CAM 网络服务
    src/cam_link/            TCP/UDP、收件、状态、作业与点动适配
    tests/                   真实 CLI 与 Python Controller 跨进程测试
  updater/                   独立 Rust Release 下载、校验与固定 root 更新服务
  mesa-update/               独立 Mesa 清单检查/下载与 root 烧录门禁
  launcher/                  Python 启动编排、就绪检查与保活
    src/bettercnc_launcher/  配置、进程与公开协议适配
    tests/                   安装后的 CLI、进程及 socket 边界测试
tools/
  diagnostics/               独立 Rust v1 兼容诊断库
  appliance/                 显式账户/目录/登录配置与固定只读 SSH 维护入口
  mesa-homing/               固定 HOMEMOD 构建与公共 API 验证适配层
vendor/cnc-mesa/              同版正式 Release 的不可变集成快照与 SOURCE.json
src/                         LinuxCNC 原生源码与统一原生构建入口
  emc/                       Task、解释器、运动、规划、运动学及接口
  hal/                       HAL 核心、组件、绑定和工具
    drivers/                 Mesa、GPIO、板卡及固件资源
    user_comps/              Modbus、VFD、USB 手轮等用户态组件
  libnml/                    NML 与数学/支持代码
  rtapi/                     实时运行环境适配
configs/                     机床与示例配置
lib/、share/、tcl/             上游运行时及工具资源
tests/、unit_tests/            原生测试
docs/                        项目说明与上游文档
.github/ci/                  按模块运行的构建和测试入口
.github/workflows/ci.yml     各模块 CI 与 CI Gate
.github/workflows/release.yml 已合并 main 且带 build-release 标签的正式 DEB 发布
```

模块内按功能、设备或总线划分，只在实现有真实差异时增加平台/CPU 目录。混合语言组件保持完整：HAL 的 C++ 绑定、Python 生成器归 HAL；桌面的 C++ UI 测试启动器归 desktop。根目录不再维护语言分类模块或它们的兼容链接。

## 通信与依赖

当前已有控制链路：

```text
QML 功能模块
  → bettercnc.desktop：PySide6 QObject，只读快照与用户操作
  → bettercnc.session：v2 Unix socket
  → betterlinuxcnc_service：会话所有权、串行命令、预览进程调度
      → bettercnc_controller.Controller：LinuxCNC API、机床规则及文件写入
      → bettercnc_preview：独立进程调用 LinuxCNC gcode 扩展
  → LinuxCNC C/C++ 核心：NML、Task、解释器、实时运动
  → HAL 与 C/C++ 设备驱动
```

`tools/diagnostics → Unix socket → Python v1 health` 为独立诊断链路；不获取控制会话，不代替 v2，不用于判断真实机床连接。Qt 的机床控制链路不经 Rust；应用更新另经独立 Rust CLI，二者不合并协议或新增 FFI。

CAM 在另一台设备生成 G-code，经 TCP 6522 发送到 Rust `betterlinuxcnc-cam-link` 二进制。`protocol` 定义帧，`inbox` 接收程序，`feedback` 回传状态，`control` 适配 v2 Unix 协议，`manual` 管理点动租约；`session` 组合连接及订阅，`discovery` 拥有 UDP 8421 发现。显式开启 auto-run 后，新文件提交同一 Python Controller 加工，重复接收和服务重启不重放。协议见 [CAM 联动协议](cam-link-protocol.md)。

不知道机床 IP 时，可显式开启 UDP 局域网发现：机床广播 `ANNOUNCE`，CAM 回复 `DISCOVER_REPLY`，机床回传 `DISCOVER_ACK`。CAM 从报文源地址取得机床 IP，再连接公布的 TCP 端口并认证。发现消息由 Rust discovery 模块拥有，根入口负责生命周期；广播握手不授予文件或机床操作权限。

| 所有者 | 公开入口 | 边界 |
| --- | --- | --- |
| Qt 界面 | `BetterCnc.<Capability>` 的 qmldir | 组件不直接访问 socket、文件、进程或硬件 |
| Qt Python | `bettercnc.desktop`、`bettercnc.session`、`bettercnc.__version__` | desktop 通过公开入口读取会话和应用版本；session 只依赖标准库 |
| 启动编排 | `bettercnc_launcher.main`、`betterlinuxcnc-launch` | 仅标准库，通过已安装 CLI 和只读 v2 Unix 协议编排，不导入服务或机床实现 |
| Rust socket | `src/lib.rs` | 只暴露诊断查询及返回数据；内部实现私有 |
| Python 服务 | `betterlinuxcnc_service`、`Controller`、`StatusReader`、`bettercnc_preview` | service 通过 controller/preview 公开入口协作，无反向依赖；StatusReader 只读取状态 |
| Rust 系统服务 | `betterlinuxcnc_services::run`、`betterlinuxcnc-cam-link` | 独立二进制，拥有网络和 inbox；仅通过公开 Unix 协议接入控制 |
| Release 更新器 | `betterlinuxcnc-updater` CLI | Qt 通过 JSON 行接口请求固定系统单元；root 独立下载校验，不接收用户包路径、URL 或命令 |
| Mesa 更新 | `betterlinuxcnc-mesa-update`、`betterlinuxcnc-mesa-flash` CLI | 检查/下载与烧录入口分离；本版无可更新位流，root 服务拒绝实际烧录 |
| 专用机配置 | `betterlinuxcnc-appliance` | 固定 postinst 仅 provision 账户/目录；plan/stage 可预演，prepare/activate 显式由 root 执行，普通更新不改登录策略 |
| SSH 维护 | `cnc-maint` 的固定 ForceCommand | 仅 help/version/status/logs/diagnostics，不提供 shell、上传、转发、提权或机床命令 |
| HAL/驱动 | 既有 HAL/RTAPI 接口 | 设备与信号适配，不依赖新增桌面或服务实现 |
| 原生核心 | 既有 EMC/NML/RTAPI API | 保持实时职责和混合语言链接边界 |

Release 更新由 `app/updater/` 独立拥有。Qt 发出无路径参数的安装请求，固定 `betterlinuxcnc-system-update.service` 以 root 校验可信包及机床状态，再协调 `linuxcnc` 的用户服务。更新器复用公开只读状态协议，不获取控制会话；版本与安装约束见 [应用更新说明](firmware-updates.md)。

LinuxCNC 自身负责解释、插补和实时控制。桌面和传输不承担伺服周期工作；命令发送不代表执行完成，重连不重放。完整协议、单位与生命周期见 [本地控制协议](local-control-protocol.md)。现有实现与测试不等于实际机床、INI/HAL 和目标机图形已经验收。

## 构建与交付

根 CMake 组合各应用模块和 appliance 工具；每个模块拥有自己的启动模板与安装规则。统一入口不编译或安装 LinuxCNC 原生核心。当前用户禁止本地及目标机构建、源码测试，包括本地 Docker；CMake/CTest、Rust 与 Python 验证仅在 GitHub CI 执行，目标机只下载已完成的 DEB 安装。应用之间继续通过公开 Python 入口或 IPC 协作，构建聚合不授予跨模块私有访问权限。

正式 DEB 额外启用 `BETTERCNC_BUILD_MESA_HOMING=ON`，由 `tools/mesa-homing/build.py` 在临时源码副本中生成本仓库 LinuxCNC 2.9.10 的 headers/halcompile，再编译 vendor 的固定 `zhulong_homing` 模块；不构建完整核心。普通 Qt/启动器检查默认关闭此选项。仅安装 `/usr/lib/linuxcnc/modules/zhulong_homing.so` 和 `/usr/share/betterlinuxcnc/homing/provenance.json`，不覆盖其他原生模块。vendor 快照的逐文件摘要、归档摘要、来源提交及发布清单摘要都由 `SOURCE.json` 固定，不能就地修订 vendor 文件。

模块的 27 个公共 API 软件场景使用同一套生成头文件；单独 CI 再运行 vendor 原有配置生成器回归和 GHDL 仿真。生成器、仿真与 ELF/20 个公开符号检查不代表板上验收。应用可安装到已有 LinuxCNC 2.9 系统，但该 HOMEMOD 仅供上游核心版本 2.9.10；显式启用配置前必须验证实际 dpkg 核心版本。Debian 13 默认 2.9.4 在包 CI 中仅验证安装生命周期，不加载此模块。未知三轴总行程时保持 inputs-only，不自动加载 HOMEMOD 或允许 HOME。

应用版本 `26.10.26.1` 独立于原生核心 `VERSION`。正式产物为 `betterlinuxcnc-qt_26.10.26.1_amd64.deb`，tag `v26.10.26.1`，Release 名称 `demo v26.10.26.1`。正式包包含 CAM、应用更新和两个 Mesa CLI 四个 Rust 二进制，通过 apt/dpkg 安装；desktop 独立 CMake 只安装 GUI，禁用系统服务的构建仅用于拆分验证。

应用代码在 `/usr/lib/betterlinuxcnc` 和 `/usr/share/betterlinuxcnc`；配置在 `/etc/betterlinuxcnc`；程序、收件、可变机床数据在 `/var/lib/betterlinuxcnc` 的专用子目录。顶层数据/缓存目录保持 root 所有，操作账户 HOME 为 `/var/lib/betterlinuxcnc/home`，用户缓存为 `/var/cache/betterlinuxcnc/user`，日志为 `/var/log/betterlinuxcnc/launcher`。现场配置和数据不随包升级覆盖，初次迁移及账户隔离须显式执行；完整目录与步骤见 [本机连接说明](linuxcnc-local-connection.md)。

原生核心保留 `src/Makefile` 和已有 Meson 构建。`src/hal/`、`src/hal/drivers/`、`src/hal/user_comps/` 均为真实源码目录，Make 的文件扫描无需跨顶层兼容链接。CI 归档覆盖当前实际文件，并测试迁移未暂存时的归档结果；上游资源和配置仍须随完整仓库保留。

HAL 内部工具以及 `src/rtapi/uspace_rtapi_app.cc` 对 HAL 私有头的既有访问仍属于原运行时内部协作，详细例外写在模块 AGENTS；目录整理不扩大私有头的公开权限。

## CI 入口

- `.github/ci/check-source.sh`：workflow、shell、Python 语法、AXIS 删除和目录迁移回归。
- `.github/ci/native-check.sh hal|motion|drivers|task|interpreter|python-extensions`：六个独立原生构建/验证；不启动控制器、模拟器、实时线程或硬件。
- 独立 `mesa-homing` job：使用共享 native 构建依赖生成当前核心头文件，编译固定模块并验证 27 个公共 API 场景、配置生成器及 GHDL 仿真；不加载模块或访问硬件。
- `.github/ci/python-check.sh service|preview|desktop|launcher`：安装当前源码构建的包并验证公共接口；预览 scope 要求真实 LinuxCNC gcode 扩展存在。
- 独立 `appliance-checks` job（Python 3.11/3.13）：检查 `tools/appliance` 源码与公开 CLI，包含配置迁移预演、原始文件保留及 SSH 命令限制；root CTest 同时注册 `appliance-provisioning`。
- `app/desktop/scripts/ci-check.sh --suite desktop|qml`：分别验证 Python 桌面后端与 QML。省略 suite 时执行原有完整检查。
- `tools/diagnostics/`、`app/cam-link/`、`app/updater/` 与 `app/mesa-update/`：`cargo fmt --check`、`cargo check --locked --all-targets`、`cargo clippy --locked --all-targets -- -D warnings`、`cargo test --locked`。跨进程测试需 Python 3.11+，可用 `SERVICE_TEST_PYTHON` 指定。
- `.github/ci/check-configs.py` 与 `config-tests/`：HAL/INI/Tcl 静态语法、文件引用及 include 环检查。

`deb-package` 在 GitHub Debian 容器构建真实应用包，验收首次/重复安装、账户与文件权限、密码/数据保留及有效 SSH/sudo 策略，上传以提交 SHA 命名的 DEB artifact，并纳入 `CI Gate`。依赖和测试用 wheel 安装局限于 CI 环境，CI 不启动机床或 SSH/显示服务。

Release workflow 只为已合并 main 且带 `build-release` 标签的 PR 发布；同一 merge SHA 必须有通过 CI Gate 的 main push run 和唯一包 artifact。仅发布 job 拥有写权限，验证摘要、版本、架构、提交与 tag，并核对 CNC-Mesa 同 tag 正式 Release 的兼容清单、来源提交与归档摘要后发布正式 latest。附带的 `mesa-release.json` 与 `CNC_MESA_PAIR.json` 保留配对来源；缺失时安全失败，可从 main 按原 PR 重试。流水线不 SSH 部署，目标机仅消费发布资产；源码归档不能替代安装包。

README 内容仍按人工维护规则处理；随目录迁移的 README 归属变化由用户任务授权，正文保持不变。根 README、Python 服务 README、`src/README.md` 和 `src/emc/usr_intf/python-interface/README.md` 中的旧服务路径仍待人工更新，当前入口以本文为准。历史文档中的旧路径不能作为当前入口。
