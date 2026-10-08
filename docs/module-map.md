# 模块职责与目录地图

2026-10-08：自有模块按“主要实现语言.职责”统一为 `python.desktop`、`python.service`、`rust.diagnostics`、`c.hal`、`c.drivers` 和 `cpp.drivers`；职责名分别表达桌面、控制服务、诊断、HAL 和设备驱动集合。Web/Tauri 应用与部署脚本已经删除。此迁移保留原有 v2 控制实现、Python 包名、Rust crate 名和命令行入口，根规范见 [AGENT.md](../AGENT.md)。

## 源码所有者

```text
python.desktop/             PySide6 + QML 桌面
  app/                      应用启动
  python/bettercnc/
    desktop/                QML 适配、文档与桌面行为
    session/                v2 Unix socket 客户端
  qml/BetterCnc/             Ui、Catalog、Manual、Toolpath、Program、Chrome
  tests/                    QML 公共界面和 Python 公共接口测试
rust.diagnostics/           独立 Rust v1 诊断通信
  src/lib.rs                probe_service、ServiceHealth 公开入口
  src/service.rs            私有协议与 Unix socket 实现
  tests/                    当前 Python 服务的跨进程协议测试
c.hal/                      HAL 核心、组件、绑定和工具
  components/               HAL 功能组件和 .comp 源码
  user_comps/               用户态组件和旧驱动构建入口
  classicladder/            梯形图能力
  utils/                    原有 HAL 命令及诊断工具
c.drivers/                  C 为主的设备驱动
  mesa-hostmot2/            HostMot2 与设备/总线实现
  pluto_*_firmware/         对应驱动的固件
  user/                     Modbus、变频器、USB 等用户态设备驱动
cpp.drivers/                C++ 设备驱动
  pendant/                  XHC 手轮驱动
python.service/             Python 服务、控制规则和隔离预览
src/                        混合 C/C++ 核心与统一原生构建入口
  emc/                      Task、解释器、运动、规划、运动学及接口
  libnml/                   NML 与数学/支持代码
  rtapi/                    实时运行环境适配
configs/                    机床与示例配置
lib/、share/、tcl/            保留的上游运行时及工具资源
tests/、unit_tests/           原生测试
.github/ci/                 按模块运行的构建和测试入口
.github/workflows/ci.yml    各模块 CI 与 CI Gate
```

模块内先按功能、设备或总线划分，只在实现有真实差异时增加平台/CPU 目录。通用代码保留一份，不建空的 x86_64/aarch64 树。Raspberry Pi、BeagleBone、HostMot2 PCI/Ethernet/SPI 的已有实现保持其能力归属。根目录的既有驱动文件保留原名。

语言前缀表示实现主体，不代表纯语言：HAL 中已有 C++ 绑定、Python 生成器仍归 HAL；Qt 的 C++ 测试启动器仍归 Qt。`c.hal/utils` 为既有 HAL 工具，不是新建通用工具桶。`rust.drivers`、`rust.hal` 等仅在引入真实实现时创建。上游 `src/` 与公共资源、配置、文档、测试目录保留原名，不适用语言前缀规则。

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

`rust.diagnostics → Unix socket → Python v1 health` 为独立诊断链路；不获取控制会话，不代替 v2，不用于判断真实机床连接。Qt 当前不经 Rust，目录迁移不会把两套协议合并或新增 FFI。

| 所有者 | 公开入口 | 边界 |
| --- | --- | --- |
| Qt 界面 | `BetterCnc.<Capability>` 的 qmldir | 组件不直接访问 socket、文件、进程或硬件 |
| Qt Python | `bettercnc.desktop`、`bettercnc.session` | desktop 只导入 session 公开入口；session 只依赖标准库 |
| Rust socket | `src/lib.rs` | 只暴露诊断查询及返回数据；内部实现私有 |
| Python 服务 | `betterlinuxcnc_service`、`Controller`、`bettercnc_preview` | service 通过 controller/preview 公开入口协作，无反向依赖 |
| HAL/驱动 | 既有 HAL/RTAPI 接口 | 设备与信号适配，不依赖新增桌面或服务实现 |
| 原生核心 | 既有 EMC/NML/RTAPI API | 保持实时职责和混合语言链接边界 |

LinuxCNC 自身负责解释、插补和实时控制。桌面和传输不承担伺服周期工作；命令发送不代表执行完成，重连不重放。完整协议、单位与生命周期见 [本地控制协议](local-control-protocol.md)。现有实现与测试不等于实际机床、INI/HAL 和目标机图形已经验收。

## 上游构建兼容路径

源码已经物理迁移，以下相对符号链接仅用于适配上游 Make、生成器、公共头文件导出及历史测试：

| 旧构建路径 | 唯一真实源码所有者 |
| --- | --- |
| `src/hal` | `c.hal` |
| `c.hal/drivers` | `c.drivers` |
| `c.hal/user_comps/mb2hal`、各迁移的 VFD 模块和 `shuttle.c` | `c.drivers/user/` 下同名能力 |
| `c.hal/user_comps/xhc-hb04.cc`、`xhc-whb04b-6` | `cpp.drivers/pendant/` 下同名能力 |

新增修改在真实模块下进行，不建立第二份源码。Make 的文件扫描显式包含三个物理目录，避免默认 `find` 跳过符号链接而漏检。CI 源码快照只归档存在的文件与链接，排除链接下面的旧索引路径；迁移尚未提交或 Web 已删除时也可运行。必须复制完整项目并保留相对链接，不能只复制 `src/`。

HAL 内部工具以及 `src/rtapi/uspace_rtapi_app.cc` 对 HAL 私有头的既有访问仍属于原运行时边界，详细例外写在模块 AGENTS；本次没有扩大私有头的公开权限，也没有宣称原生库已经完全解耦。

## CI 入口

- `.github/ci/check-source.sh`：workflow、shell、Python 语法、AXIS 删除和目录迁移回归。
- `.github/ci/native-check.sh hal|motion|drivers|task|interpreter|python-extensions`：六个独立原生构建/验证；不启动控制器、模拟器、实时线程或硬件。
- `.github/ci/python-check.sh service|preview|desktop`：安装当前源码构建的包并验证公共接口；预览 scope 要求真实 LinuxCNC gcode 扩展存在。
- `python.desktop/scripts/ci-check.sh --suite desktop|qml`：分别验证 Python 桌面后端与 QML。省略 suite 时执行原有完整检查。
- `rust.diagnostics/`：`cargo fmt --check`、`cargo check --locked --all-targets`、`cargo clippy --locked --all-targets -- -D warnings`、`cargo test --locked`。跨进程测试需 Python 3.11+，可用 `SERVICE_TEST_PYTHON` 指定。
- `.github/ci/check-configs.py` 与 `config-tests/`：HAL/INI/Tcl 静态语法、文件引用及 include 环检查。

CI 只构建、测试和上传必要诊断，不部署、不发布、不安装到目标机。依赖和测试用 wheel 安装局限于 CI 环境。模块标准打包元数据保留，CI 不运行发布包打包步骤。

README 内容仍按人工维护规则处理；随目录迁移的 README 归属变化由用户任务授权，正文保持不变。根 README、Python 服务 README、`src/README.md` 和 `src/emc/usr_intf/python-interface/README.md` 中的旧服务路径仍待人工更新，当前入口以本文为准。历史文档中的旧路径不能作为当前入口。
