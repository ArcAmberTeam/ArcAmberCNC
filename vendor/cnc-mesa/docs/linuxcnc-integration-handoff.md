# 烛龙 V2 回零接入交接

交付给正在处理 LinuxCNC 安装包和目标机集成的“评估项目架构特点”任务。用户后续约定：CNC-Mesa 使用现有 main 直接提交；ArcAmberCNC 使用现有 kihon 向 main 提 PR（接入任务负责替换原 PR #27）。所有提交邮箱 IwakuraTorei@outlook.com。只在 GitHub CI 构建和测试，经合并、Release DEB 后安装。不要新建分支，不在本机或目标机编译测试，不直接改目标配置，不通过安装脚本触发回零、点动或烧录 FPGA。

## 已知信息与证据

| 项目 | 当前依据 |
| --- | --- |
| 接法 | 用户最新确认：机械常闭 NC，输入经开关接 GND；未触碰导通，触碰断开 |
| 轴输入 | 用户指定 GPIO 20=X、21=Y、22=Z；这是 HostMot2 GPIO 编号，不是 DB25 物理针号 |
| 最新物理轴定义 | 按用户最新照片/观察方向：X 是前后、行程 420 mm；Y 是左右、行程 275 mm；Z 是上下、行程 90 mm；此定义取代此前“X 左右、Y 前后”的描述 |
| 物理回零方向 | X 向后、Y 向左、Z 向下；这些物理方向对应的机床坐标/电机命令正负号仍待标定，不能从照片或旧配置推定 |
| 极性 | `.in` 原值：未触碰 0、触碰 1、松开 0；`.in_not` 是软件反相，不使用 |
| 退开距离 | 沿用当前模块参数 5 mm；第一次退开和第二次触碰后的退开均为此距离 |
| 总行程 | 用户已确认从开关触发点到另一端的可用行程：X 420、Y 275、Z 90 mm；通用模板保留 null，不自动继承某台机床的实测值 |
| 电机通道映射 | 未完成现场核对，且已观察到逻辑轴与物理轴不一致，见下节；GPIO 开关映射正确不代表电机输出映射正确 |

原厂 `docs/hardware/烛龙V2 使用说明 必看.doc` 的开关图只给出 GPIO—开关—GND 接法，没有内部反相电路和 NC/NO 端子标注。本次极性依据最新用户接法及运行时读数。HostMot2 的 `.in_not` 反相实现在 LinuxCNC `src/hal/drivers/mesa-hostmot2/ioport.c`。

2026-10-26 最初的只读审计（当时尚未接入 HOMEMOD）：GPIO020/021/022 为输入，静止 `.in=FALSE/.in_not=TRUE`。当时运行配置的三轴 `home-sw` 和正负限位信号只有 joint 接收端，没有 GPIO 写入源；INI 没有搜索/定位速度，也没加载 `zhulong_homing`。所以该阶段“GPIO 有变化、joint home/limit 不变化”是未接线，不是开关检测失败。

接入任务随后反馈的手按验证（目标日志 UTC 19:12–19:14，约 100 ms 采样）：

- 三路均观察到快速点按的 FALSE→TRUE→FALSE。
- GPIO021 长按多次约 1.34–1.44 s；用户确认均为 Y 轴同一个开关，保持期间采样未见中断。
- GPIO022 长按约 1.03/1.96 s；GPIO020 约 1.34/1.44 s；保持期间采样未见中断，松开均 FALSE。
- 接入任务后续取得用户确认：GPIO020 的另一次长按约 6.914 s 对应 X；前述 GPIO022 的两次长按对应 Z。三轴物理标识和高有效均已核对。100 ms 采样不证明不存在毫秒级触点抖动，仍保留伺服去抖。

通用模板 `switch_inputs_verified` 默认仍为 false，防止未经验证的新安装继承旧机验证。接入方可以根据上述实测为该台机器记录 true，并录入已确认的行程；这仅表示输入和行程已核对，不是电机映射验收或回零启用许可。

## 电机映射与方向调试前置条件

接入任务报告：此前现场 HOME ALL 时，逻辑 X / stepgen.00 实际带动了被识别为行程 275 mm 的物理 Y 轴，随后 GPIO021 限位触发。这个观察暴露了逻辑轴、输出通道和物理轴对应关系的问题；用户后续用照片明确了上表的物理定义。其余通道对应哪根物理轴、各通道运动正负向尚未验证，不能据此推断成只需交换 X/Y，更不能猜测 Z 的通道或反转方向。

`zhulong_homing` 的参数与下列 HAL/INI 表以 joint.0/1/2 已分别驱动真实 X/Y/Z 为前提。电机映射错误时，给逻辑 X 设置 420 mm 行程不能保护实际被驱动的 275 mm Y 轴；开关读数正确和仿真通过也不能证明这层映射正确。

旧参考实现使用逻辑 X−/Y+/Z−。它尚未按最新的“X 向后、Y 向左、Z 向下”物理定义标定，当前不可执行；尤其不能再把“向后”直接写成 X+ 或 X−，也不能凭“向下”确定 Z 电机的符号。HOMEMOD 当前校验该旧符号约定；若现场结果需要不同约定，须在确认映射后让模块和配置一致适配并通过 CI，不能只翻转某个 HOME 参数或电机引脚试错。

应用接入必须分别记录三轴开关验证、实际行程、电机通道到物理轴的映射、正负向验证状态；任一映射或方向未确认时，控制后端拒绝单轴 HOME 和 HOME ALL，界面显示具体缺项。只有显式现场调试记录完成、配置与记录一致后才能解除回零限制；不能从 `switch_inputs_verified=true`、旧的 homed 标志、版本升级或已有 INI 自动推导电机已验证。

本次配套版本保持 HOMEMOD、VHDL、引脚与运动方向不变。机床级电机映射/方向门禁由应用实现；本仓库参考生成器仅校验已声明的输入、方向和行程参数，并不会测量或证明电机连接，因此不能单独作为启用依据。现场核对与后续配置修改按应用的已发布更新流程处理，不在目标机临时补丁、自动交换引脚或用烧录来试错。

## 源码与公开接口

本地来源仓库 `/Users/goodgirlkihon/Documents/CNC-Mesa`。交接消息提供固定提交及源码归档 SHA-256；将该快照作为有来源的第三方模块纳入现有 PR，不依赖目标机现存源码目录。

| 路径 | 用途与边界 |
| --- | --- |
| `homing/zhulong_homing.comp` | 公共 HAL 模块入口，`option homemod`，模块名 `zhulong_homing` |
| `homing/prepare.py` | 将相邻 `src/homing.c` 内联到 `.build/homing/zhulong_homing.comp`，不编译、不安装 |
| `homing/src/homing.c` | HOMEMOD 实现，使用 LinuxCNC 标准回零 API 和 joint 轨迹规划器；不直接驱动 FPGA |
| `homing/provenance.json` | 原始来源提交、文件 SHA 和修改范围，保留 GPL 头及来源 |
| `mesa/board/zhulong-v2.json` | 公共板卡配置：GPIO、方向、退开距离、`active_low=false` |
| `linuxcnc/homing.json` | 调试参数模板：速度、开关验证旗标、待测总行程 |
| `linuxcnc/prepare.py` | 公共 `prepare(settings, destination, *, board_path=...)` 与 CLI，仅生成独立供应商参考配置 |
| `tests/test_linuxcnc_config.py` | 通过公开生成接口检查极性、路由、顺序、输入校验、禁止覆盖和 CLI |
| `tests/homing/test_homing.c`、`homing/upstream/simple_tp.*`、`tools/test_homing.py` | 公共 HOMEMOD API 的 27 个 XYZ 正常/故障/取消场景，仿真不接硬件 |

最小构建只需 `homing/`，测试和配置集成还需表中其余文件、`linuxcnc/vendor-reference/` 与根 Makefile。供应商参考配置用于生成器测试，不能覆盖 `/etc/betterlinuxcnc/machine`。不需要导入 FPGA 位流、HostMot2 HDL 或固件烧录工具。

## GitHub CI 与 DEB

在 GitHub runner 上、使用与 Release 核心相同的 LinuxCNC 头文件、RTAPI 类型及架构运行：

```sh
make prepare-homing
cd .build/homing
halcompile --compile zhulong_homing.comp
```

`halcompile` 必须来自 Release 所用 LinuxCNC 构建环境。它通过自身 `Makefile.modinc` 找到开发头文件；不要把其他 LinuxCNC 版本预编译的 `.so` 直接拼入安装包。

将生成的 `zhulong_homing.so` 安装到该 LinuxCNC 的实时模块目录，位置与 `homemod.so`、`motmod.so` 一致（按实际 `EMC2_RTLIB_DIR`/包清单确定，不硬编码另一套安装前缀）。验证 DEB 确实包含该文件，并检查目标架构和动态依赖。准备工具和测试代码不必装到目标运行目录。

当前仓库测试入口：

```sh
# 完整 CNC-Mesa 快照：原始来源/模块边界、Python 回归、HDL 映射、HOMEMOD
make check test-hdl test-homing

# 只纳入最小回零快照时：配置与实际 HOMEMOD 编译/公共 API 仿真
python3 -m unittest discover -s tests -p test_linuxcnc_config.py -v
make test-homing
```

完整检查依赖 Python3、GHDL、make、gcc 和 LinuxCNC 开发包。最小检查不需要 GHDL；`test-homing` 先真正运行 `halcompile --compile`，再运行 3 轴 × 9 场景：正常、初始已触发、开关永不触发、首次触发后不释放、第二次后不释放、搜索取消、退开取消、反方向限位、错误方向参数。全部在 CI 仿真；不连接真实控制器。

本次本地没有执行构建或源码测试。交接时结果以现有 PR 的 GitHub CI 为准；失败则修复快照/接入并重跑，不能标记为实体机验收通过。

发布版本由根目录 `release.json` 定义，当前配对 `v26.10.26.4`。推送匹配版本标签后，CI 必须先通过全部检查才发布源包、最小接入包、`mesa-release.json` 和 `SHA256SUMS`。清单包括板型号、变体、源提交、应用版本、各归档摘要和固件可用状态；源码版本与应用版本不一致时拒绝生成。

当前没有可证明由本次源码构建并在板验证的新位流，因此清单明确 `firmware.available=false`，`asset/sha256/size=null`，`origin=unavailable`，`verification.implementation/timing/board_approved` 均为 false。独立 Rust 更新服务可以发现/下载匹配版本的源码和元数据，必须据此判定没有可刷固件；不能从完整源码包里提取原厂参考 `.bit` 冒充新版。未来真实位流需完成 ISE 构建、约束/时序和板级验证，再制定独立的固件产物发布规则，要求 `origin=ci-build` 和相应验收字段为 true。

## VHDL 交付

现有 `firmware/zhulong-v2/PIN_ZHULONG_V2_34.vhd` 已将 20/21/22 留作普通 GPIO（IOPortTag + NullTag），六路 STEP/DIR 映射不变。`hostmot2/upstream/hostmot2.vhd` 使用原始 `WordPR` 管理方向/输出、`WordRB` 原样回读输入；输出 invert 寄存器不参与输入回读。因此本功能不需要增加 FPGA 回零状态机，也不需要修改输入极性或烧录新位流。

新增 `tests/hdl/nc_inputs_tb.vhd`，直接实例化未修改的 Mesa `wordpr.vhd` 和 `wordrb.vhd`，按板卡真实的 2 个 17 位端口验证 20/21/22：默认输入高阻、闭合 0、断开 1、保持、释放、多路同时触发、跨端口隔离、未选中总线高阻，以及输出反相设置不影响输入。原有 `board_profile_tb.vhd` 继续验证全部 34 路引脚和六路步进映射。

通过 `python3 tools/test_hdl.py` 在 GitHub CI 运行。最小 HDL 快照包含 `tools/test_hdl.py`、`tests/hdl/*.vhd`、`firmware/zhulong-v2/PIN_ZHULONG_V2_34.vhd` 和上游 `IDROMConst.vhd`、`i92_x9card.vhd`、`wordpr.vhd`、`wordrb.vhd`，保留文件版权和原始 SHA。仿真验证数字逻辑边界，不等于模拟板上模拟电路、完成 ISE 全工程时序或还原了供应商位流。

## 选择性合并配置

配置归接入任务所有：持久 INI/HAL 位于 `/etc/betterlinuxcnc/machine`，可变状态位于 `/var/lib/betterlinuxcnc/machine`。使用安装包已有的备份、升级迁移和回滚链路；不要整份导入供应商 INI/HAL。审计时运行路径曾为 `/home/teto/ArcAmberCNC/configs/zhulong-v2/烛龙V2.ini`，这只是审计快照，接入时应从 launcher 和进程参数确认实际文件。

1. 安装模块可以先完成；回零启用必须同时满足三轴输入验证、实测总行程、电机通道/物理轴映射和正负向验证，以及模块存在。未满足时在控制入口明确返回缺项（例如“电机映射未验证”），不要退回无开关的即时置零，也不要把 HOME_SEARCH_VEL=0 当作本功能的可用状态。
2. 合并工具只修改下面的回零字段/信号。保留 stepgen 引脚、脉冲时序、SCALE、速度/加速度、PID、驱动使能、急停、主轴、运动学、显示界面及原有网络服务。
3. 合并前检查实际 HALFILE 列表及所有 home/limit 输入连接；已有其他写入源、重复 `debounce` 实例、不同 GPIO 映射或已接的另一侧限位都不能静默覆盖。验证失败时保留原配置并报告冲突。
4. 新内容在临时配置副本中校验后再通过包的配置迁移流程安装。一次性同步 INI 和 HAL；重复升级应幂等，不追加重复 `loadrt`、`addf` 或 net。未知条件时仅安装模块和禁用的参数模板，不加载或调用回零。

### HAL 合并点

以下信号和符号描述旧参考实现，不能当作最新物理轴定义已经标定后的运行配置。实际电机通道与方向未验收前，应用必须保持回零禁用。

先加载 `debounce`，将其函数安排在 `hm2_7i92.0.read` 之后、`motion-command-handler` 和 `motion-controller` 之前。若已有 debounce，分配未占用通道并相应改名，不能重复加载。

```hal
loadrt debounce cfg=3
setp debounce.0.delay 5
# 在已有 servo-thread 调度中插入，不是简单追加在文件末尾：
# addf hm2_7i92.0.read servo-thread
addf debounce.0 servo-thread
# addf motion-command-handler servo-thread
# addf motion-controller servo-thread

net x-home-raw hm2_7i92.0.gpio.020.in => debounce.0.0.in
net y-home-raw hm2_7i92.0.gpio.021.in => debounce.0.1.in
net z-home-raw hm2_7i92.0.gpio.022.in => debounce.0.2.in

net x-home-sw debounce.0.0.out => joint.0.home-sw-in joint.0.neg-lim-sw-in
net y-home-sw debounce.0.1.out => joint.1.home-sw-in joint.1.pos-lim-sw-in
net z-home-sw debounce.0.2.out => joint.2.home-sw-in joint.2.neg-lim-sw-in
```

原文件已有 `net x-home-sw => joint.0.home-sw-in` 等语句时复用该信号，避免重复定义；把对应方向的旧 `x-neg-limit/y-pos-limit/z-neg-limit` 空信号接收端迁到同一个 home 信号。另一侧的限位接线保留。不要 `setp` GPIO 为输出。5 个周期的去抖时间由实际 servo period 决定，例如 1 ms 周期时约 5 ms。

### INI 合并点

```ini
[EMCMOT]
HOMEMOD = zhulong_homing
```

LinuxCNC 启动脚本会先加载 HOMEMOD，再加载运动 HAL 文件；不要在 HAL 再次 `loadrt zhulong_homing`。确认启动命令没有 `-m` 覆盖它。

| 字段 | JOINT_0 / X | JOINT_1 / Y | JOINT_2 / Z |
| --- | ---: | ---: | ---: |
| HOME | 0 | 0 | 0 |
| HOME_OFFSET | -5 | +5 | -5 |
| HOME_SEARCH_VEL | -2 | +2 | -2 |
| HOME_LATCH_VEL | -0.5 | +0.5 | -0.5 |
| HOME_FINAL_VEL | 2 | 2 | 2 |
| HOME_SEQUENCE | 1 | 2 | 3 |
| HOME_IGNORE_LIMITS | YES | YES | YES |
| HOME_USE_INDEX | NO | NO | NO |

`HOME_IGNORE_LIMITS=YES` 用于共用的回零方向限位；模块仍检查反方向限位并中止。未安装另一侧限位不能被描述成已有硬件保护。A/B/C 尚无回零方案，`HOME_SEQUENCE=101` 排除 HOME ALL；它们的单独回零请求也不能冒充本次 XYZ 功能。

设实测“从开关向内可用总行程”为 L、退开距离 d=5，生成器保留两端各 d，跨度 S=L−2d，要求 L>3d。在旧符号约定下，X/Z 的 AXIS 和 JOINT 软限位为 `[0,S]`，Y 为 `[-S,0]`。这是尚未按新物理定义验收的参考策略，接入时须先完成坐标符号和有效行程核对，不扩大现有合法软限位来绕过校验。未知或不足时拒绝启用；不得填入测试里的 200 mm。

按用户确认的 X420/Y275/Z90，可计算跨度 X410/Y265/Z80 mm；但这些跨度的正负坐标区间必须等方向标定后确定。只有旧 X−/Y+/Z−约定在现场得到验证时，才对应 X `[0,410]`、Y `[-265,0]`、Z `[0,80]`。当前不能把这些带符号的参考区间或 Z−直接用于新物理定义，也不能用它们解除回零门禁。

## 控制入口及验收

CAM/Rust/桌面沿用 LinuxCNC 已有 HOME 命令进入控制层，再调用标准 LinuxCNC joint 回零接口。三轴全部验证及配置就绪前，后端也要拒绝请求，不能只禁用前端按钮。连接 CAM、上传 G-code、安装包启动都不自动触发回零。

完整流程：按确认方向寻找→首次触发停止→向内完整退 5 mm→慢速再次触发→再次向内退 5 mm→机床坐标为 0、该轴 homed。初始开关已触发时先离开再搜索；退开后开关不释放、距离不正确、取消或异常限位时不报告 homed。

接入验收先检查软件：包内模块、配置迁移幂等性、未配置请求的拒绝、模拟两次触碰和故障取消。装包后只能先在未使能/急停状态读开关，确认原始输入、去抖输出和 joint home/对应 limit 一致。实体回零需要实际行程与现场条件齐备后单独执行；当前交接不代表已执行实体回零，也不授权安装后自动运动。
