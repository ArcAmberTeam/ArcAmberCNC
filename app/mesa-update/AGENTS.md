# 独立 Mesa 发布检查与烧录入口

遵循根 `AGENT.md`；本地及目标机不构建、不运行源码测试，验证由 GitHub CI 执行。`src/lib.rs::run_update`、`run_flash` 和两个 CLI 是唯一公开入口，内部模块不对外开放。不导入 `app/updater` 私有实现，不依赖控制服务、桌面或 HAL 的内部代码，不建立通用工具模块。README 只由人工维护。

- `betterlinuxcnc-mesa-update check|status|download` 仅供固定 `linuxcnc` 普通账户使用。独立系统 timer/service 以该账户执行 `check`；timer 不下载、不停机、不烧录。`check` 查询固定 `ArcAmberTeam/ArcAmberCNC` 与 `ArcAmberTeam/CNC-Mesa` latest 正式 Release，报告共同版本。`download` 只查询已完整安装的 `betterlinuxcnc-qt` 版本对应的 `v<version>`，禁止任意版本、地址、路径或命令参数。
- `betterlinuxcnc-mesa-flash status|apply-system` 是另一个独立二进制和 root 系统服务。root `apply-system` 每次独立从官方 Release 拉取元数据和位流，不读取用户缓存或用户 manifest。当前仅能验证下载，所有实际烧录均返回 `blocked` 和非零退出；没有 mesaflash、systemctl、控制端点或硬件命令。无 polkit 放行、GUI 烧录触发、自动停机或刷写。未来必须单独批准固定目标硬件、只读空闲门禁、正常停止、备份、烧录及回读流程后才能实现真正 apply。
- 两个 CLI stdout 使用 schema_version=1 JSON：component、phase、message、updated_unix、installed_app_version、available_version、app_latest_version、mesa_latest_version、manifest、firmware_downloaded、flash_enabled。`flash_enabled` 当前恒为 false；`firmware_downloaded` 仅说明本进程缓存通过摘要验证，绝不代表板卡已刷或其运行版本。公开状态不是烧录授权凭据。
- 固定 `mesa-release.json`：schema_version=1、version、tag_name、compatible_app_version、source_commit、board=zhulong-v2、variant=PIN_ZHULONG_V2_34、fpga=xc6slx9、package=tqg144、physical_constraints_verified；artifacts.source/integration 各含 asset、sha256、size_bytes；firmware 含 available、asset、sha256、size、origin、reason 和嵌套 verification 的 implementation/timing/board_approved。
- 本版为合法源码发布：firmware.available=false、asset/sha256/size=null、origin=unavailable、三项验证=false。必须显示“源码更新、无固件”，不拒掉整个 manifest，也不能用原厂旧 bit 冒充新构建。未来 available=true 必须 origin=ci-build、三项验证及 physical_constraints_verified 全 true；版本、板卡、FPGA/package、tag 解析后的 source_commit、官方 asset URL/size 与 SHA-256 都需匹配。
- HTTPS 仅访问固定官方仓库与 GitHub Release CDN；禁用环境代理，限定响应大小、超时和重定向，不读取任意 URL 或仓库配置。HTTP 错误不回显签名下载 URL。缺失资产、预发布、来源不明、摘要不符、部分安装或版本不配对均失败关闭。
- 低权限缓存固定 `/var/cache/betterlinuxcnc/user/mesa-update`，root 缓存固定 `/var/cache/betterlinuxcnc/mesa-flash`，root 公开结果固定 `/var/lib/betterlinuxcnc/mesa-flash/status.json`。root 父目录不能由普通账户写入。目录逐层用 fd 和 O_NOFOLLOW 打开并检查属主/权限，缓存 0700、文件 0600，公开目录 0755/status 0644。使用独立锁和 fsync/原子改名；不跟随链接、特殊文件或硬链接读取缓存状态。
- CMake 独立安装两 bin 和三个精确 system unit。安装包不启用/启动 timer 或 flash；专用机激活是否启用 timer 由 appliance 的显式配置流程负责。新增安装路径同步更新 updater 包边界白名单。
- CI 应执行 cargo fmt --check、cargo check --locked --all-targets、cargo clippy --locked --all-targets -- -D warnings 和 cargo test --locked。测试覆盖两公开进程参数边界、版本配对、source-only、源提交、官方 URL、摘要、root 独立请求和缓存路径/链接；使用受控 HTTP 适配、临时文件，不访问网络或真实机床，不执行烧录命令。
