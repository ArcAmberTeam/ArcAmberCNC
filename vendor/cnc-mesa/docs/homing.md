# 回零

输入 20/21/22 分别对应 X/Y/Z。用户最新确认开关常闭接 GND，未触碰导通、触碰断开；使用 `.in`，正常为 0、触发为 1。板卡配置 `homing.active_low=false`，生成器按该值选择 `.in`；只有经过验证的低有效配置才使用 `.in_not`。经过 5 个伺服周期去抖后，同时连接回零和对应方向的限位。

流程：X−、Y+、Z−方向寻找开关；触发后停止，退到距第一次触发位置向内 5 mm；慢速再次触发；向内退 5 mm，最终机床坐标为 0。退开距离由板卡配置的 homing.distance_mm 决定。实际重复精度取决于开关、去抖延迟与运动跟随误差。

LinuxCNC 标准回零第一次退开通常在开关释放后就停止，本模块改为完整的定长退开。第二次触发位置通过 HOME_OFFSET 设定，最终回到 HOME=0。轨迹、加减速、取消回零和坐标继续由 LinuxCNC 管理，FPGA 不绕过它独立发脉冲。

配置文件：linuxcnc/homing.json。search_speed_mm_s 为第一次寻找速度；latch_speed_mm_s 为第二次慢速寻找速度；return_speed_mm_s 为最终退回速度。switch_inputs_verified 只有在三轴物理标识和未触碰、触碰、释放状态均已核对后才能设为 true。usable_travel_from_switch_mm 是各轴从开关向内的实测可用总行程，尚未提供，保留 null。5 mm 是沿用当前实现的退开参数，不能当成总行程。生成器在两端各预留一个退开距离，再生成正负软限位；还要求软限位跨度大于退开距离，因此当前每轴总行程必须大于 15 mm。

GitHub CI 编译（与安装包相同的 LinuxCNC 开发环境）：

    make prepare-homing
    cd .build/homing
    halcompile --compile zhulong_homing.comp
    cd ../..
    make test-homing

CI 将模块放进 release DEB，目标机只安装 DEB，不现场编译或手工改运行配置。集成步骤和状态记录见 [LinuxCNC 接入交接](linuxcnc-integration-handoff.md)。

生成独立参考配置的接口：`python3 linuxcnc/prepare.py --settings /path/to/verified-homing.json --output /path/to/empty-directory`。默认设置故意不能生成可启用的回零配置。生成器只在输入验证与实测行程完整时写文件，拒绝覆盖非空输出目录；生成结果沿用供应商的运动参数，不能用来覆盖已经调好的机床配置。接入方按交接文档选择性合并回零字段。HOME ALL 顺序为 X、Y、Z；A/B/C 未指定回零方法，排除在 HOME ALL 外。

验证通过公共 HOMEMOD 接口执行，使用 LinuxCNC 单轴轨迹规划器模拟运动，检查状态、距离、故障和取消。软件测试不代表实体机已完成回零验收。
