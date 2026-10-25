# 应用 Release 更新

“设置 → 关于本机”的“更新固件”检查 `ArcAmberTeam/ArcAmberCNC` 最新正式 GitHub Release，下载并校验当前 Debian 架构的应用包。这里更新 GUI、控制服务、CAM、启动器、更新器与专用机维护工具；不刷写控制卡或电机固件，不覆盖源码工作区；LinuxCNC 原生核心仍由 `linuxcnc-uspace` 独立系统包管理。

## 26.10.26.1 发布约定

| 项目 | 当前约定 |
| --- | --- |
| Release 名称 | `demo v26.10.26.1` |
| Tag | `v26.10.26.1` |
| Debian Package / Version | `betterlinuxcnc-qt` / `26.10.26.1` |
| amd64 安装包 | `betterlinuxcnc-qt_26.10.26.1_amd64.deb` |
| 校验资产 | `SHA256SUMS`，每个文件名只出现一次 |
| 配对资产 | 同 tag 的 CNC-Mesa `mesa-release.json` 与本仓库的 `CNC_MESA_PAIR.json` |
| Release 类型 | 正式、非 draft、非 prerelease，并设为 latest |

名称中的 `demo` 不改变发布类型。更新器读取 `/releases/latest`，不是按名称选择版本。Tag 去掉开头的 `v` 后必须与 `.deb` 的 Version 完全一致；文件名架构、包元数据架构和 `dpkg --print-architecture` 必须相同，同版本和降级均拒绝。

根 CMake、desktop Python 包与公开 `bettercnc.__version__` 使用同一个应用版本。根 `VERSION` 的 `2.9.10` 是 LinuxCNC 核心版本；Rust crate 内部版本也不能用于判断应用是否需要更新。

`ArcAmberTeam/CNC-Mesa` 同版 Release 提供源码与集成资料。清单固定 `schema_version=1`、`board=zhulong-v2`、`variant=PIN_ZHULONG_V2_34`，`version` 与 `compatible_app_version` 均为 `26.10.26.1`，`source_commit` 必须等于 tag 指向且位于该仓库 `main` 的提交。其他描述性 metadata 可以扩展；应用、板型、来源与验证声明必须符合发布契约。

本版 `firmware.available=false`，`asset`、`sha256`、`size` 均为 null，`origin=unavailable`；`firmware.verification` 内的 `implementation`、`timing`、`board_approved` 和顶层 `physical_constraints_verified` 均为 false。没有新 ISE 位流不阻止应用发布，但不允许烧录。原厂 bit 即使包含在参考源码归档中，也不能当作更新载荷。

独立 `app/mesa-update/` 安装两个 Rust CLI：`betterlinuxcnc-mesa-update` 负责检查/状态/下载，`betterlinuxcnc-mesa-flash` 拥有独立的固定 root 服务入口。本版烧录入口拒绝实际烧录，没有通用 Polkit 授权；检查服务以 `linuxcnc` 运行，安装不会自动启动检查 timer 或烧录服务。应用 DEB 更新与控制卡烧录的权限、状态和失败结果分别处理。

同版集成归档以不可变快照存放在 `vendor/cnc-mesa`，`SOURCE.json` 记录 Release、来源提交、归档/清单摘要和逐文件摘要。发布门禁还核对远端清单与应用实际编译的这份固定快照，不能只匹配版本号。DEB 内的 `zhulong_homing.so` 是 LinuxCNC HOMEMOD 软件模块，不是 FPGA 位流；它只允许配合上游核心版本 2.9.10 启用。配置激活必须验证实际 dpkg 核心版本，未知总行程继续使用 inputs-only，不能自动加载模块或触发 HOME。

每个包需要 Release asset 的有效 `sha256:` digest，或同一 Release 的 `SHA256SUMS` 中唯一的对应记录。下载地址限定当前仓库并全程使用 HTTPS。Release 缺失、架构不匹配、多个候选包、版本或校验记录不合法时，界面显示原因并保留当前安装。本功能不自行创建或发布 Release。

## 固定系统服务安装边界

Qt 只调用 `betterlinuxcnc-updater fetch --current-version <版本>`、`status` 和无附加参数的 `install`，使用 JSON 行观察结果。它不能向安装请求附加包路径、URL、目标版本、socket 或任意命令。

1. 普通用户检查并下载到私有缓存，界面显示下载和校验进度。下载完成后可请求“安装并重启”。
2. `install` 只允许系统配置中的 `linuxcnc` 账户请求固定 `betterlinuxcnc-system-update.service`。Polkit 只允许启动该单元，不授予通用 systemd 管理、pkexec 或 sudo；不弹出通用管理员授权来绕过限制。
3. 系统单元以 root 运行固定 `betterlinuxcnc-updater apply-system`，只读 root 所有的 `/etc/betterlinuxcnc/updater.json`。该文件固定 `user=linuxcnc`、`config=/etc/betterlinuxcnc/launcher.json`；额外字段或其他账户、路径被拒绝。
4. root 服务独立从正式 Release 重新下载与校验，不复用用户可写的 `.deb`、manifest 或环境代理。它核对包名、版本、架构、大小和 SHA-256，并流式检查 Debian data/control 归档：拒绝越界路径、链接、特殊文件、危险权限、非 root 所有者及未知 control 文件。维护脚本只允许内容、属主和权限完全匹配的固定 `postinst`，用于幂等 `provision`；其他脚本或脚本改动均拒绝。唯一允许的 conffile 为 `/etc/betterlinuxcnc/updater.json`，已有安装目的路径也必须可信。
5. 通过公开 `machine.status` 只读确认最新状态。未知状态、使能、暂停、运动、主轴或待处理任务会阻止安装；不取得控制会话，不发送停机、回零、点动或其他机床命令。
6. 下载验证后再次检查状态，按原状态正常停止 `linuxcnc` 的启动器用户服务，确认控制 socket 与原生锁消失。
7. root 服务运行无附加参数的 `/usr/sbin/betterlinuxcnc-appliance backup`，备份当前配置、可变机床数据和固定主机策略。命令无法启动、备份或校验失败时都不调用 apt；已有快照保留，控制系统保持停止并报告失败。
8. 备份成功后使用固定 `/usr/bin/apt-get --yes --no-remove install` 安装，之后核对 dpkg 实际版本。仅成功时恢复原本运行的受管启动器；失败时保持停止并报告原因，不强杀核心或启动混合版本。

依赖包括 systemd 用户会话、Polkit、apt/dpkg 和可验证的 Debian 安装包；macOS 预览不能执行安装。root 身份仍承担包管理，操作员和 SSH 维护账户不因此获得 root shell。安装包自动 `provision` 账户和目录，保留密码与数据；普通软件更新不会运行 `prepare` 或 `activate`、修改登录策略或导入机床配置。

## 安装目录与保留数据

| 路径 | 所有权与用途 |
| --- | --- |
| `/usr/bin/betterlinuxcnc*`、`/usr/sbin/betterlinuxcnc-appliance` | root 所有的已安装命令 |
| `/usr/lib/betterlinuxcnc`、`/usr/share/betterlinuxcnc` | root 所有的应用模块和 QML |
| `/usr/lib/linuxcnc/modules/zhulong_homing.so` | 唯一额外安装的原生 HOMEMOD；仅供 LinuxCNC 2.9.10 显式启用 |
| `/usr/share/betterlinuxcnc/homing/provenance.json` | 模块摘要、构建源码 SHA、核心版本/头文件摘要、vendor 来源和软件场景记录 |
| `/etc/betterlinuxcnc/launcher.json`、`machine/` | 现场配置，由显式迁移建立；应用包不包含这些文件 |
| `/etc/betterlinuxcnc/updater.json` | root 所有的固定更新配置，Debian conffile |
| `/var/lib/betterlinuxcnc/{programs,inbox,machine}` | 程序、CAM 收件、刀具表/参数/位置等运行数据，由 `linuxcnc` 写入 |
| `/var/cache/betterlinuxcnc/user/betterlinuxcnc/update` | 用户检查和下载缓存，不作为 root 安装输入 |
| `/var/cache/betterlinuxcnc/update` | root 私有下载缓存与 `install.log` |
| `/var/lib/betterlinuxcnc/update/status.json` | root 写入、用户只读的安装状态 |
| `/var/lib/betterlinuxcnc/recovery/snapshots` | root 私有的更新前快照，成功创建并校验后保留最近 3 份 |
| `/var/log/betterlinuxcnc/launcher` | 启动器及子进程日志；更新不清理历史日志 |

`/var/lib/betterlinuxcnc` 与 `/var/cache/betterlinuxcnc` 顶层始终由 root 拥有且不可由普通用户写入；不能把整个树交给操作账户。普通用户仅拥有规定的子目录。示例配置安装到 `/usr/share/doc/betterlinuxcnc-qt/examples/launcher.example.json`，不会覆盖真实配置。

GUI 退出不会终止系统更新服务；重新打开后读取系统公开状态。`cnc-maint` 的固定 `logs` 命令只读取规定的启动器进程日志，不授予读取 root 私有更新日志的权限；安装失败由受控管理员通过系统 journal 和私有 `install.log` 排查。

更新前快照覆盖 `/etc/betterlinuxcnc`、`/var/lib/betterlinuxcnc/machine` 的参数/刀具表等数据，以及工具管理的固定主机策略，并记录 SHA-256、应用版本与时间。它不包含大型程序库、CAM 收件、日志、缓存、账户密码或 SSH 私钥。旧快照仅在新快照创建并校验成功后轮换；失败不能删除已有备份后继续安装。

备份不自动恢复文件、不回退包版本、不修改机床状态。需要恢复时由受控管理员审查版本、摘要和现场配置，具体入口见 [备份与人工恢复边界](linuxcnc-local-connection.md#更新前备份与人工恢复边界)。同盘快照不能抵御磁盘故障，不能替代程序数据、凭据和异盘备份。

## 构建、发布与验证

当前用户禁止本地及目标机构建，包括本地 Docker。所有编译、源码测试和产包只能在 GitHub 托管 runner 进行；目标机下载完整 DEB 后安装，不拉源码自行编译。流水线入口为 `.github/workflows/ci.yml`、`.github/workflows/release.yml` 与 `.github/ci/deb-package.sh`。

1. 后续应用变更沿现有 `kihon` 提交，通过 `kihon → main` 的 PR 合并。需要发布的 PR 添加 `build-release` 标签；未合并的 PR、没有标签的合并以及其他分支都不发布。
2. Module CI 的 `deb-package` 在 Debian 13 amd64 容器构建完整包，执行真实首次和重复安装。它检查账户/目录权限、原密码与数据保留，并在隔离容器验证 SSH/sudo 实际策略；不启动机床、图形或 SSH 服务。
3. 成功后上传 `betterlinuxcnc-deb-<SHA>` artifact，内含真实 `.deb`、`SHA256SUMS` 和 `SOURCE_COMMIT`；`CI Gate` 同时要求模块测试和包验收通过。
4. Release workflow 在 main CI 完成或已合并 PR 加标签时检查资格，只读取同一 merge SHA 的成功 main push CI 和唯一 artifact。仅发布 job 拥有仓库内容写权限，不检出或执行 PR 源码。
5. 发布 job 再核对源码 SHA、包名、四段版本、amd64 架构、SHA-256 和 tag 指向，并只读检查 CNC-Mesa 同 tag 的正式 Release：清单摘要、来源提交及源码/集成归档的摘要和大小均须一致。创建 draft 前与正式发布前各检查一次；配对缺失或检查期间变化时不正式发布。
6. 成功后上传 `.deb`、`SHA256SUMS`、配对清单原字节 `mesa-release.json` 和包含两仓来源提交、Release/asset ID、清单摘要的 `CNC_MESA_PAIR.json`，发布 `demo v26.10.26.1` 为正式 latest。GitHub 自动附带的源码 zip/tar 不是安装包。

CNC-Mesa 先发布，应用后发布；跨仓库仅公开读取，不需要 PAT 或跨仓库写权限。若应用流水线先完成，可在配对 Release 就绪后重跑失败发布 job，或从 `main` 手动运行 Release workflow 并提供原已合并 PR 编号。重试仍检查标签授权、同一 merge SHA、成功 CI 和原 artifact；既有资产必须摘要一致，不替换已发布文件，也不让迟到的旧版本降低 latest 版本。

正式包必须启用系统服务并包含 CAM、应用更新、Mesa 检查、Mesa 烧录门禁四个真实目标架构 Rust 二进制；发布 CI 从该提交源码构建，不复用开发机产物。`BETTERCNC_CAM_LINK_BINARY`、`BETTERCNC_UPDATER_BINARY`、`BETTERCNC_MESA_UPDATE_BINARY` 和 `BETTERCNC_MESA_FLASH_BINARY` 仅保留供 CI 拆分验证；`BETTERCNC_BUILD_SYSTEM_SERVICES=OFF` 的测试包和 desktop 单独安装不作为正式发布包。CPack 使用 `DESTDIR` 暂存，真实安装验收只写入一次性 CI 容器。

正式包同时启用 `BETTERCNC_BUILD_MESA_HOMING=ON`。构建适配层从本仓库 2.9.10 源码生成头文件和 halcompile，只编译固定模块并运行 27 个公共 API 场景；包验收检查真实 ELF、20 个公开符号与来源记录。Debian 13 容器默认核心 2.9.4 仅用于应用包安装/重复安装验证，绝不加载这个模块，也不宣称其 ABI 兼容；实际目标机核心版本与配置启用需单独核对。

启动器暂存安装回归继续核对版本、真实二进制、配置保留、systemd 单元与 `.deb` 布局；独立 appliance job 覆盖迁移预演和维护命令限制，Rust updater job 覆盖真实 Debian 归档及固定 postinst 正负路径。发布前必须通过同一提交的完整 `CI Gate`。流水线只发布安装资产，不连接或部署目标机。

目标机安装、账户迁移、专用会话和连接验收按 [本机连接说明](linuxcnc-local-connection.md) 执行。包验证和只读状态检查不等于真实更新、图形会话或机床运动验收，必须分别记录实测结果。
