# Qt GUI 的 LinuxCNC 外部接口测试

在仓库根目录运行：

```sh
python.desktop/.venv/bin/python python.desktop/tests/interactive/main.py
```

无需安装、启动或连接真实 LinuxCNC、HAL、虚拟机及硬件。这个入口只用于测试，生产入口仍维持原来的行为。

## 注入位置

```text
原始 qml/Main.qml（简易 / 专业布局）
  → 原始 bettercnc.desktop.DesktopBackend
  → 私有 Unix socket（真实 v2 会话、命令及预览分页）
  → 原始 betterlinuxcnc_service.serve
  → 原始 bettercnc_controller.Controller
  → 测试 LinuxCNCInterface：stat / command / error_channel / ini
```

测试宿主使用现有 `Controller(module=...)`、`serve(controller_factory=..., process_factory=...)` 公共入口。没有修改、继承或 monkey patch 生产 GUI、后端、控制器和服务；不通过替换 GUI 快照来跳过控制规则。服务在测试宿主的独立线程中运行，控制器仍在服务自己的工作线程中串行调用。

刀路预览的进程工厂也从外部注入：测试替身返回受限 G0/G1 几何，服务仍负责异步任务和分页，GUI 仍使用原预览接收流程。预览区明确显示“非 LinuxCNC 解释器结果”。

每次运行建立独立的 `/tmp/cnc-api-*` 目录（0700）和 socket（0600），生成测试 INI、刀具表、参数文件和 QSettings，并复制演示程序。退出时清理临时目录。测试不会更改用户的生产设置；在文件对话框中另选的文件仍由原程序按原有规则处理。

## 交互步骤

1. 在独立“外部注入测试控制台”点击“显示主窗口”。初始为急停、未上电、未回零。
2. 原 GUI 中按 F1 解除急停，再按 F2 上电；简易布局选择“设备控制”，点击“全部回零”。模拟回零耗时约 1 秒，回零基准为 X0 Y0 Z5。
3. 按 R 或点击“运行”。演示程序走 40 × 30 mm 的矩形刀具中心线，Z=-1，最后抬至 Z5，关闭主轴。未启用刀径补偿。
4. 按 P 暂停，观察坐标保持；按 S 继续；按 Esc 停止。专业布局支持 T 单段；两个布局共享同一个控制会话，可以在运行或暂停期间切换。
5. 在测试控制台选择 1×、2×、5× 或 10×，加速测试运动与回零。120 ms 命令回执延迟保持真实墙钟时间，不随速度倍率缩短。
6. 在控制台点击“注入外部急停”“断开 NML”或“注入驱动报警”，观察原 GUI 的状态、禁用条件和错误提示。主窗口最小化后可访问被遮住的控制台；“显示主窗口”恢复主窗口。

NML 断开模拟状态/命令通道不可用，socket 服务本身仍在线。进行中的程序可以继续推进；它不等于急停。恢复连接后读取新状态，原控制器不重放未完成命令。外部急停会停止运动并断电，解除急停后仍需重新上电。驱动报警通过原 `error_channel` 流程显示，并停止测试运动。

可选参数：

```sh
python.desktop/.venv/bin/python python.desktop/tests/interactive/main.py \
  --interface professional \
  --report python.desktop/artifacts/simulation/interface-interaction.json
```

`--program /绝对路径/示例.ngc` 加载另一份受支持的程序副本；`--capture /tmp/interface.png` 在启动后截取主窗口并退出。报告保留原桌面快照、接口命令序号、延迟回执和故障注入事件，最近最多 500 条事件。

## 支持范围

- 模拟 `stat().poll()`、`command()` 的递增序号及延迟回执、`error_channel().poll()`、INI 查询。
- 急停、电源、模式切换、回零/取消回零、连续/增量点动、停止点动、打开程序、运行/暂停/继续/停止/单段。
- 进给/快移倍率影响运动速度；最大速度限制程序运动；主轴、冷却、制动及开关状态反馈。
- 受限程序必须明确初始化 G21/G17/G90/G94/G40/G49/G54/G80，使用数值 G0/G1、XYZ、F、S 和 M2/M3/M5/M9，并以 M2 结束。
- MDI、对刀、坐标系修改、换刀、刀具表重载、从指定行启动、圆弧、宏及子程序尚未实现，会报告失败，不伪造成功。选择停和程序段跳过仅有开关状态；解析器不接收 M1 或 `/` 程序段。

这是外部 API 行为替身，线性位置反馈用于 GUI 测试。不模拟加速度、伺服误差、编码器、物理限位/回零开关、HAL 时序、碰撞或材料去除，不等同于真实 LinuxCNC 解释器和机床验收。

## 文件职责与验证

| 文件 | 职责 |
| --- | --- |
| `tests/interactive/main.py` | 外部组装原窗口、原桌面后端与测试宿主 |
| `tests/interactive/service_host.py` | 私有 socket、原服务及预览工厂注入、临时配置生命周期 |
| `tests/interactive/vendor.py` | LinuxCNC Python API 替身、延迟回执、线性运动与故障输入 |
| `tests/interactive/linear_program.py` | 严格受限的演示程序解析；预览与运动共用 |
| `tests/interactive/backend.py`、`Controls.qml` | 独立测试控制台，通过线程安全队列注入故障 |
| `tests/test_simulation.py` | 原 Controller 的确定性测试及原 DesktopBackend + 原服务的 socket 集成测试 |
| `tests/programs/rectangle-demo.ngc` | 矩形演示加工程序 |

表中路径相对于 `python.desktop/`。

```sh
QT_QPA_PLATFORM=offscreen python.desktop/.venv/bin/python python.desktop/tests/test_simulation.py -v
```

测试使用公开接口，不读取生产对象的私有字段。覆盖延迟回执、回零状态、几何及拒绝不支持程序、暂停/继续/停止/完成、单段、外部急停、断线不重放、点动停止、倍率、错误通道，以及真实 socket 上的准备→运行→暂停→继续→完成→断线恢复。原项目回归仍使用 `ctest --test-dir python.desktop/build --output-on-failure`；本测试独立执行，不更改生产构建入口。
