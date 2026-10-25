# 回零

输入 20/21/22 分别对应 X/Y/Z。用户最新确认开关常闭接 GND，未触碰导通、触碰断开；使用 `.in`，正常为 0、触发为 1。板卡配置 `homing.active_low=false`，生成器按该值选择 `.in`；只有经过验证的低有效配置才使用 `.in_not`。经过 5 个伺服周期去抖后，同时连接回零和对应方向的限位。

参考流程：沿已标定的回零方向寻找开关；触发后停止，退到距第一次触发位置向内 5 mm；慢速再次触发；向内退 5 mm，最终机床坐标为 0。退开距离由板卡配置的 homing.distance_mm 决定。实际重复精度取决于开关、去抖延迟与运动跟随误差。

用户最新物理定义为 X 前后（420 mm）向后回零、Y 左右（275 mm）向左回零、Z 上下（90 mm）向下回零，取代此前 X 左右/Y 前后的描述。代码保留的旧 X−/Y+/Z−参考符号尚未按此定义标定，不是可直接执行的机床配置；物理方向不能从照片直接换算成电机或机床坐标正负号。

LinuxCNC 标准回零第一次退开通常在开关释放后就停止，本模块改为完整的定长退开。第二次触发位置通过 HOME_OFFSET 设定，最终回到 HOME=0。轨迹、加减速、取消回零和坐标继续由 LinuxCNC 管理，FPGA 不绕过它独立发脉冲。

配置文件：linuxcnc/homing.json。search_speed_mm_s 为第一次寻找速度；latch_speed_mm_s 为第二次慢速寻找速度；return_speed_mm_s 为最终退回速度。switch_inputs_verified 只有在三轴开关物理标识和未触碰、触碰、释放状态均已核对后才能设为 true。usable_travel_from_switch_mm 是各轴从开关向内的实测可用总行程；通用模板保留 null，机床实例使用其自身确认的数值，本次目标机已确认 X420/Y275/Z90 mm。5 mm 是沿用当前实现的退开参数，不能当成总行程。生成器在两端各预留一个退开距离，再生成正负软限位；还要求软限位跨度大于退开距离，因此当前每轴总行程必须大于 15 mm。

开关验证不能代替电机输出映射与方向验证。现场已报告逻辑 X / stepgen.00 带动物理 Y 并触发 GPIO021，其余通道仍待核对。应用后端须在三轴电机映射和方向显式验收前拒绝 HOME/HOME ALL；不得凭已有行程、开关验证或生成器通过而解除限制。具体证据与接入条件见 [LinuxCNC 接入交接](linuxcnc-integration-handoff.md)。

GitHub CI 编译（与安装包相同的 LinuxCNC 开发环境）：

    make prepare-homing
    cd .build/homing
    halcompile --compile zhulong_homing.comp
    cd ../..
    make test-homing

CI 将模块放进 release DEB，目标机只安装 DEB，不现场编译或手工改运行配置。集成步骤和状态记录见 [LinuxCNC 接入交接](linuxcnc-integration-handoff.md)。

生成独立参考配置的接口：`python3 linuxcnc/prepare.py --settings /path/to/verified-homing.json --output /path/to/empty-directory`。默认设置故意不能生成可启用的回零配置。生成器只在输入验证与实测行程完整时写文件，拒绝覆盖非空输出目录；生成结果沿用供应商的运动参数，不能用来覆盖已经调好的机床配置。接入方按交接文档选择性合并回零字段。HOME ALL 顺序为 X、Y、Z；A/B/C 未指定回零方法，排除在 HOME ALL 外。

验证通过公共 HOMEMOD 接口执行，使用 LinuxCNC 单轴轨迹规划器模拟运动，检查状态、距离、故障和取消。软件测试不代表实体机已完成回零验收。

## v26.10.26.5 signed and parallel profile

The HOMEMOD now derives the search direction and opposite-limit selection from the sign of HOME_OFFSET. The original generator remains a conservative commissioning reference; it must not overwrite an installed, tuned machine profile. The application owns the exact reviewed v1/v4 migration.

The operator confirmed stepgen.01=X (positive forward), stepgen.00=Y (positive right), and stepgen.02=Z with negative STEP_SCALE (positive up). The installed v5 profile homes all axes in the negative direction: X back, Y left, Z down, with independent GPIO020/021/022 inputs. Travel is 420/275/90 mm. HOME stays 0 and HOME_OFFSET stays -5; minimum soft limits become -0.1 mm, giving feedback quantization margin while staying 4.9 mm inside the switch. Maximum limits remain 410/265/80 mm.

Public HAL input `joint.N.home-backoff-vel` is a positive speed in machine units/second, default 2. It is sampled and validated at HOME_START, then remains fixed for that attempt. XYZ accepts values greater than zero and at most 2; invalid/non-finite values abort the entire request. It controls both initial switch clearance and the full first retreat, independently of HOME_SEARCH_VEL. The standard C HOMEMOD API remains unchanged.

The v5 application sets XYZ HOME_SEQUENCE=1 for concurrent independent homing. Search is X/Y -15 and Z -5 mm/s; first backoff is +2; latch is -1; final retreat to HOME is X/Y 5 and Z 2 mm/s. Failure or cancellation clears homed state and disables every planner in the current request, including peers that already finished. Other requests and unrelated previously homed joints are not touched.

The public API harness covers both signed reference profiles (54 scenarios) and parallel operation (27 scenarios). The parallel harness uses the LinuxCNC planner at 750 mm/s², 1 ms steps and five complete periods of input delay. It measures peak penetration and checks a 0.5 mm software budget within the operator-reported minimum 1 mm switch overrun. These results do not verify real motor deceleration, step loss, latency or collision clearance. The first physical parallel test requires no tool, an empty table, and a verified collision-free full XYZ envelope including downward Z. Machine acceptance remains pending; CI never starts hardware.
