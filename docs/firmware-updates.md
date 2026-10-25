# 应用 Release 更新

“设置 → 关于本机”底部的“更新固件”检查 `ArcAmberTeam/ArcAmberCNC` 的最新正式 GitHub Release，下载并校验当前 Debian 架构的应用安装包。该名称指整套应用软件更新，不刷写驱动板、运动控制卡或电机固件，也不拉取或覆盖源码工作区。

## 发布产物

- 包名：`betterlinuxcnc-qt`，文件名：`betterlinuxcnc-qt_<Debian版本>_<架构>.deb`；例如 `betterlinuxcnc-qt_0.3.0_amd64.deb`。
- Release tag：`v<Debian版本>` 或 `<Debian版本>`，与安装包 Version 精确一致。只接受正式版本，不读取 draft/prerelease。
- 包架构与 `dpkg --print-architecture` 一致；包名必须是上述应用包。拒绝同版本安装和降级。
- 每个包必须有 GitHub Release asset 的 `sha256:` digest，或同一 Release 的 `SHA256SUMS` 中唯一的 SHA-256 校验记录。下载入口限定当前仓库且全程 HTTPS。
- 应用版本来自已安装 Debian 包与根 CMake 的产品版本。仓库根 `VERSION` 是 LinuxCNC 核心版本，不用于判断 GUI 更新。

仓库尚无正式 Release、没有对应架构包或缺少校验信息时，界面显示具体原因，不修改当前安装。本功能不创建或发布 Release。

## 下载和安装

1. 点击“更新固件”检查并下载，显示进度；完整下载后校验大小、SHA-256、包名、版本与架构。
2. “安装并重启”只在校验完成后出现。先停止加工与主轴、关闭机床使能；Rust 再通过公开 `machine.status` 读取实时状态，不取得控制会话或发送机床动作。
3. 独立的 `betterlinuxcnc-update.service` systemd 用户单元执行安装。它正常停止原启动器，并确认控制 socket 与原生核心锁都已释放；状态不明或保留进程时拒绝安装，不强杀核心。
4. 系统 `pkexec` 授权后调用固定 `/usr/bin/apt-get` 安装已校验的包，核对实际安装版本。只有成功时才重启原先受管的启动器；安装失败保留日志，不自动启动可能处于混合版本的控制系统。

正常安装依赖 Debian、systemd 用户会话、pkexec 授权代理和 apt/dpkg。macOS 开发预览显示不可用状态。该流程不等于目标机更新验收；实际管理员授权、安装和机床重启需要在目标机验证。

Rust 实现位于 `app/updater/`；Qt 适配器只调用 `betterlinuxcnc-updater fetch --current-version <版本>`、`status` 与 `install [--socket <路径>]` 的公开 JSON 行接口。下载、安装锁与状态存入当前用户私有的 `${XDG_CACHE_HOME:-~/.cache}/betterlinuxcnc/update/`；安装日志为该目录的 `install.log`。独立安装服务在 GUI 退出后继续运行，重新打开 GUI 后可读取完成或错误状态。

验证命令：在 `app/updater/` 运行 `cargo fmt --check`、`cargo check --locked --all-targets`、`cargo clippy --locked --all-targets -- -D warnings`、`cargo test --locked`；从根 CMake 构建运行 Qt、Python 公共接口与模块边界检查。测试只使用受控接口，不执行真实安装或连接机床。
