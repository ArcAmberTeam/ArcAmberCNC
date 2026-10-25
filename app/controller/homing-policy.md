# 专用机回零配置契约

本文件规定 Controller 从 LinuxCNC 公开 INI API 读取的有效配置，不是机床实测记录。
配置生成器必须验证 commissioning JSON；包内迁移工具接受显式的三轴实测行程参数，
再选择性更新现有配置。2026-10-26 用户给定 X420/Y275/Z90 mm，包内工具可据此准备
下列配置；参数确认不代表配置已部署或机床运动已验收。缺少实测值时仍禁止回零。

## HOME ALL 与运动权限

`HOME_SEQUENCE` 省略或正数大于 100 的 joint 不参加 HOME ALL。负数保留原生同步组含义，
排序使用绝对值；首个序号须为 0 或 1，其后不能断号。Controller 在发送命令前拒绝空集合
或断号集合，防止原生序列提前结束后界面一直等待。单 joint 的合法即时回零仍可用于普通
LinuxCNC 配置，不要求开关或搜索速度。

Controller 的状态新增以下字段：

- `homeAllJoints`：配置参加 HOME ALL 的 joint 索引。
- `homeAllHomed`：该非空集合的原始 `homed` 位均为真；它不是运动许可。
- `homingConfigured`：HOME ALL 集合有效且满足适用的专用机政策。
- `homingMessage`：专用机政策缺少必要配置时的说明。

`machine.home-all` 只等待该集合完成，`machine.unhome-all` 仍等待所有 joint 解除回零。
原有 `homed` 数组完整保留各 joint 的真实状态。MDI、自动加工、世界坐标点动不会因为
XYZ HOME ALL 完成就忽略 ABC；专用机仍要求所有活动 joint 真实回零。
用户已确认本机只有 XYZ；本次显式迁移删除原模板的未使用 ABC joint，最终活动集合为三轴。
因此真实 XYZ 全部完成后可以满足原有运动门禁，无需伪造 ABC 的状态。

## 烛龙 V2 有效 INI

以下任一条件启用严格政策：`BETTERCNC_KIOSK=1`、`[EMCMOT] HOMEMOD=zhulong_homing`、
或 `[BETTERCNC_HOMING] PROFILE=zhulong-v2`。缺少配置时所有 HOME 请求拒绝，普通
LinuxCNC 的即时回零语义不受影响。专用机的 `NO_FORCE_HOMING=1` 是配置错误，不会绕过联锁。

启用前同时满足：

- `[EMCMOT] HOMEMOD = zhulong_homing`，`[TRAJ] LINEAR_UNITS = mm`。
- `[BETTERCNC_HOMING] PROFILE = zhulong-v2`。
- `[BETTERCNC_HOMING] SWITCH_INPUTS_VERIFIED = YES`。
- `[BETTERCNC_HOMING] TRAVEL_X_MM`、`TRAVEL_Y_MM`、`TRAVEL_Z_MM` 均为有限实测值，且大于 15。
  这些数值表示从各开关向内的可用总行程；5 mm 退开距离不能代替它们。
- 已知 trivkins 映射为 X→joint 0、Y→joint 1、Z→joint 2；HOME ALL 集合恰为 `[0, 1, 2]`。
- 三轴 `HOME = 0`，`HOME_OFFSET` 依次为 `-5, +5, -5`，`HOME_SEQUENCE` 依次为 `1, 2, 3`。
- `HOME_SEARCH_VEL` 和 `HOME_LATCH_VEL` 方向依次为负、正、负，
  `0 < abs(latch) < abs(search) <= 5`，`0 < HOME_FINAL_VEL <= 5`。
- 三轴 `HOME_IGNORE_LIMITS = YES`、`HOME_USE_INDEX = NO`。
- 令实测总行程为 L，则 X/Z 的 AXIS 和 JOINT 软限位均包含零点、非空且处于 `[0, L-10]`，
  Y 则处于 `[-L+10, 0]`。允许保留更窄的已有安全范围，不能为了通过验证扩大限位。

严格政策下只有 joint 0/1/2 可以发起 HOME。ABC 尚未定义回零方案时应使用
`HOME_SEQUENCE = 101`，它们不能通过单轴 HOME 冒充本功能的回零。
完整配置即使通过校验，也只允许用户显式提出回零请求；连接、上传、安装和启动不触发运动。

本契约只校验已启用的 INI。HAL GPIO 接线、去抖调度、来源版本与模块安装须由包内集成
流程另行验证；Controller 不导入 appliance 或 HOMEMOD 私有实现，也不直接操作 HAL。

包内公开入口为 `betterlinuxcnc-appliance stage|prepare --source-config <原launcher.json>
--zhulong-homing-travel-mm 420 275 90 --zhulong-xyz-only`；`stage` 另需 `--destination <新目录>`。
它仅更新回零字段与所需 HAL 接线，三轴 AXIS/JOINT 限位依次为 `[0,410]`、`[-265,0]`、
`[0,80]`；Z 回零后的正方向向内。参数、PID、步进时序、主轴和其他接线保留。
`--zhulong-xyz-only` 明确删除已审计的 ABC INI 区段与完整的旧 PID/stepgen/HALUI 接线；
未知或不完整的 ABC 模式拒绝迁移。它把 JOINTS 改为 3，运动学、坐标与显示几何改为 XYZ，
板卡 `num_stepgens=6` 能力不变。参数文件和刀表保留；新机床坐标为 X/Z 向内正、Y 向内负，
实际回零后必须现场核对 G54 等工件坐标，不能把旧工件坐标直接视为已验证的加工坐标。
GPIO020/021/022 的 `.in` 经 5 个伺服周期去抖，分别接 X 负、Y 正、Z 负 home/limit；
另一侧 limit 保留。`prepare` 要求已安装核心与开发包为相同的 2.9.10 版本，核对 HOMEMOD
来源与摘要、六个关键原生头文件摘要；`stage` 只生成待安装检查的副本。
互斥选项 `--zhulong-inputs-only` 只接入已验证开关，保持原回零参数，设置
`motion.homing-inhibit=true`，不启用 HOMEMOD，也不能在 Controller 中授权 HOME。
