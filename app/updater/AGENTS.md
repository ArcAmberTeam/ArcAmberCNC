# Rust Release 更新服务

遵循根目录 `AGENT.md`。`src/lib.rs::run` 和 `betterlinuxcnc-updater` CLI 为公开入口，内部实现私有。模块不依赖 CAM、Qt、Python 应用实现、HAL 或 LinuxCNC 扩展。

- 普通 `linuxcnc` 账户没有 sudo/root 权限。GUI 可查询、下载和触发固定 `betterlinuxcnc-system-update.service`；安装入口不接受包路径、URL、版本、socket 或 APT 选项。polkit 仅允许 linuxcnc 账户 start 该 unit 和独立的 `betterlinuxcnc-mesa-flash.service`，不授予其他 systemd 管理或 pkexec 权限。
- root broker 仅由系统 unit 调用 `apply-system`，独立查询固定 ArcAmberTeam/ArcAmberCNC latest 正式 Release，重新下载、验证 SHA-256、Debian 包名/版本/架构和防回退。不得读取用户缓存或 manifest 安装。所有外部命令使用固定绝对路径和净化环境，网络禁用环境代理。
- 系统配置 `/etc/betterlinuxcnc/updater.json` 仅含 `user=linuxcnc` 和 `config=/etc/betterlinuxcnc/launcher.json`；两个配置文件及每级目录均检查 root 属主、不可由组/其他账户写入且无符号链接。root 缓存、锁和安装日志位于 `/var/cache/betterlinuxcnc/update`，公开只读 JSON 状态位于 `/var/lib/betterlinuxcnc/update/status.json`。两个顶层父目录保持 root 所有；账户 HOME 与用户 cache 位于各自独立子目录。
- 包内容通过固定 dpkg-deb 和 python3 -I -S 的标准库 tarfile 流解析，禁止提取执行。只接受既有应用系统命令、应用 lib/share/doc 子树和逐项允许的集成文件；拒绝路径遍历、全部链接、特殊节点、危险权限和未知控制文件。新增安装路径必须同时更新白名单及正/负测试。
- Mesa 独立模块仅增加精确命令 `betterlinuxcnc-mesa-update`、`betterlinuxcnc-mesa-flash` 和两个同名系统 `.service`、检查用 `betterlinuxcnc-mesa-update.timer`；不允许烧录 timer、任意 mesaflash 二进制或额外系统配置。其固件验证和未来烧录职责归 `app/mesa-update`，本更新器不导入其内部实现。
- 另允许精确 `/usr/lib/linuxcnc/modules/zhulong_homing.so`，不放宽该目录或允许替换其他原生模块；来源与 core/dev ABI 校验由独立 homing 适配器拥有。
- 固定公开 `mesa-maintenance` 只供 root 服务使用，不接受参数；与 APT 共用同一 root 更新锁，调用独立 Mesa CLI `prepare-system` 验证官方固件后，复用安全状态门禁、正常停止及固定备份，再启动唯一的 `write-system`。FD3 承载随机挑战及 probe/write/verify/complete 的逐步授权，FD4 继承同一 flock；每步都重新确认控制 socket/native lock 不存在。父进程不通过环境变量、任意命令、用户路径或解锁后继续操作授予权限。备份失败不生成写入进程。进入停止后保留 runtime mask，成功回读也不重启或 reload 卡；输出待受控断电重启，硬件实现仍归 Mesa 模块。
- 唯一允许的 maintainer script 是与 `src/updater/package_members.py::APPROVED_POSTINST` 逐字节一致、root:root 且模式 0755 的 `postinst`。其 `configure` 分支只执行固定 `/usr/sbin/betterlinuxcnc-appliance provision`，幂等设置账户和固定目录权限，并调用用户已授权的固定 v1 XYZ 配置迁移（精确摘要匹配、核心停止、模块验证、目录原子交换），不修改密码、SSH、桌面会话或启动机床；所有其他脚本和任何字节改动均拒绝。`tools/appliance/packaging/postinst` 是对应打包入口，CI 必须验证两份内容一致。保持此脚本字节长期稳定，包含 LF 和末尾换行；不能随 provision 实现升级而改写脚本，否则已安装的旧更新器会拒绝后续包。未批准 sysusers/tmpfiles 或其他新增系统路径。
- 安装前读取公开 `machine.status`，拒绝未知、暂停、运动、排队任务、主轴运转或使能状态。root 只读连接固定账户私有 socket；用户 systemd 操作通过固定 runuser 降权并净化环境。停止前重复检查，临时 mask 启动器并正常 stop；控制端点或原生锁仍在则拒绝安装。用户会话不可查询时拒绝安装。
- 固定 root unit 显式保留 CAP_SETUID/CAP_SETGID ambient capabilities，确保 User=root、NoNewPrivileges 与沙箱组合下仍能降到 linuxcnc。实际普通账户不因此获得这些 capabilities。GitHub 托管 runner 通过真实 systemd 单元限制与 runuser/id 验证降权，不能只用 systemctl 替身声称完成此项验收。
- 启动器正常停止且控制 socket、原生锁均已释放后，先以净化环境执行固定 `/usr/sbin/betterlinuxcnc-appliance backup`，成功才调用 APT。备份由 appliance 独立拥有，只包含固定机床配置、可变机床状态及主机策略，保存于 root 私有 snapshots；不接受 GUI 提供的源、目的路径或命令。备份命令无法启动或返回失败都拒绝安装，控制系统保持停止。
- 失败不报告成功、不自动启动可能混合版本的控制系统。仅 apt 成功且安装版本复核后恢复原来运行的受管启动器；不得授予 GUI 固件、INI/HAL、任意文件和系统命令写权限。
- 测试使用临时目录、发布元数据、真实 Unix socket 和受控进程，不访问真实机床、不执行真实安装、不发布 Release。依用户当前要求，只在 GitHub CI 运行 cargo fmt --check、cargo check --locked --all-targets、cargo clippy --locked --all-targets -- -D warnings、cargo test --locked；本地和目标机都不构建或测试。真实 Debian 归档回归须覆盖固定 postinst 的允许、内容篡改及其他脚本的拒绝，不执行包中的脚本。README 只由人工维护。
