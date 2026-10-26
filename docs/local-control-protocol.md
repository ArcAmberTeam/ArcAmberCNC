# 本地控制协议 v2

端点使用 AF_UNIX stream。父目录为同一用户所有的 0700 目录，socket 为 0600；服务不覆盖已有 socket。每帧为四字节大端无符号长度，随后 UTF-8 JSON，正文最大 65,536 字节。重复 JSON 字段、非有限数、非法版本、未知字段、无效参数与超长帧拒绝处理。

v1 保持 `{version:1, request_id, method:"health"}` 的旧格式，返回历史诊断结果和 `machine_connected:false`。它不获取控制会话，也不代表实际机床状态；由独立 `tools/diagnostics` 库保留兼容。

v2 请求：

```json
{"version":2,"request_id":"unique-id","method":"session.status","params":{"jog_lease":false}}
```

成功返回同版本和 request_id，以及对象 `result`；失败返回 `error:{code,message}`。同一连接的 request_id 不得复用。客户端不自动重发命令；发送后丢失回执视为结果未知。

| 方法 | 参数 | 返回 |
| --- | --- | --- |
| `machine.status` | 空对象 | 独立只读状态：运行状态、运动执行行、任务执行行、刀具、主轴、冷却；不要求附着控制会话 |
| `session.attach` | 可选 `ini_path` | 状态快照；INI 不匹配或已有所有者则拒绝 |
| `session.status` | 可选布尔 `jog_lease` | 最新机床快照；只有已建立点动租约才能续期 |
| `command.execute` | `action`、对象 `payload` | `accepted` 与 `snapshot`；accepted 不是执行完成 |
| `preview.start` | 绝对 `path` | `job_id`；上下文由服务取得，客户端不能替换 |
| `preview.read` | `job_id`、非负整数 `offset` | 最多 256 段、next_offset、busy、done、units、bounds、error、warnings、truncated |
| `preview.cancel` | `job_id` | `cancelled:true` |

除 `machine.status` 和 `session.attach` 外，每个 v2 方法都要求当前连接持有会话。`machine.status` 通过独立 `StatusReader` 在工作线程读取 `linuxcnc.stat`，不建立 command/error 通道，不获取控制所有权，也不续租点动；没有桌面控制会话时仍可查询。服务最多一个控制所有者，一个预览任务归属于该连接；控制连接断开释放所有权、取消预览和未发送的后续命令。观察者断开不改变机床状态。其他 LinuxCNC 工具不受此 socket 所有权约束，应在部署时协调。

`machine.status` 中 `currentLine` 仅来自 `motion_line`，`taskLine` 来自任务层的 `current_line`，`readLine` 来自解释器预读的 `read_line`；这些位置分别返回，不能用任务行或预读行替代运动执行行。`progressPercent` 保持 null；循环、子程序和各段耗时不同，行号不能表示准确完成比例。`programState` 为 idle/running/paused/busy/estop/off/unknown；idle 不能证明某项作业已成功完成。详细外部接口见 [CAM 联动协议](cam-link-protocol.md)。

`machine.status` 还返回 `busy`（解释器、执行状态或队列尚未静止）、`velocity`（原生单位/秒；缺失或非有限值为 null）与 `nativeCommandState`（NML `stat.state` 的 RCS_DONE/RCS_EXEC/RCS_ERROR 分别归一为 done/executing/error，其余为 unknown）。`nativeCommandState` 仅表示原生通道观察值，不表示某个 GUI 请求已经完成。服务若仍跟踪 accepted/pending/sent/unknown 的桌面命令，会额外返回该请求的 `commandState`；不要将两者混同。更新器必须同时确认新鲜原生状态、队列和请求状态可停止，并由启动器正常退出；只读观察不能替代机床物理联锁。

`machine.status.configuration` 为只读机床配置，无法读取或离线时为 null；旧服务可缺省该字段。格式为 `{schemaVersion:1, axes:[...], kinematics:string|null}`。轴列表按 `XYZABCUVW` 排序，仅包含 NML `axis_mask` 中实际启用的轴，不根据 joint 数或预留 INI 段推断。配置来自当前运行实例的 `ini_filename`，通过 LinuxCNC INI 读取器处理 include。

每个轴包含 `name`、`kind`（linear/rotary）、`unit`（mm/deg）、`min`、`max`、`maxVelocity`。ABC 为旋转轴，其余为直线轴。软限位来自 `AXIS_<name>.MIN_LIMIT/MAX_LIMIT`，按原生单位比例转换为毫米或度；最大速度来自 `MAX_VELOCITY`，转换为每分钟。未知或无效数值为 null；上下限颠倒时两者均为 null。软限位范围属于机床坐标，不能直接用作工件坐标下的刀路边界，也不代表机械总行程。`kinematics` 为 INI 的 `KINS.KINEMATICS`（最多 256 字符），不包含配置文件路径。存在四/五个轴不证明支持四/五轴同时加工，客户端不得据此猜测旋转中心或自动套用运动学模型。

## 状态与操作

`connected` 是 LinuxCNC 状态有效，Qt 另外维护 `serviceConnected`，不得将二者混为一谈。位置数组按 `XYZABCUVW` 排列；长度为 LinuxCNC 原生单位、角度为原生角度单位，`linearUnits` 是原生单位/毫米，`angularUnits` 是原生单位/度。joint 编号独立于 axis，未知运动学映射不能猜测。预览输出 XYZ 的单位统一为毫米。

完整刀表保留在服务内供预览使用；网络快照使用 `toolTableRevision` 标识变化。网络错误历史保留最近 20 条，每条消息最多 1024 UTF-8 字节，附 errorHistoryCount/errorsTruncated，避免大刀表或长错误导致状态帧超限。

`commandState` 为 idle、pending、sent、completed、error、unknown；pending 可能仍在等待模式切换，sent 等待 LinuxCNC 回执，completed 表示该条命令已确认，**不等于整段加工程序结束**。当状态忙、条件改变或回执被外部写入者推进时，不继续发送后续步骤。

| action | payload |
| --- | --- |
| `machine.estop`、`machine.power` | 可选 enabled；缺省根据新鲜状态切换 |
| `machine.mode`、`motion.mode` | mode: manual/mdi 或 joint/world |
| `machine.debug` | value 为 0–2147483647 的整数；等待 stat.debug 确认 |
| `machine.home`、`machine.unhome` | 明确 joint；全回零使用 machine.home-all |
| `jog.start` | axis 字符或明确 joint 整数、mode、direction ±1、velocity 原生单位/秒、increment 原生单位 |
| `jog.stop` | 空对象；取消尚未发出的 start 并停止本会话点动 |
| `mdi.execute` | 单行 text，最多 254 字节 |
| `program.run`、`program.step`、`program.pause`、`program.resume`、`program.stop` | 空对象；program.run-line 带 1 起始 line |
| `spindle.cw`、`spindle.ccw` | 可选 RPM speed；无默认配置时要求明确转速 |
| `spindle.stop`、`spindle.increase`、`spindle.decrease`、`spindle.brake` | 抱闸可带 enabled |
| `coolant.flood`、`coolant.mist` | 可选 enabled |
| `override.feed`、`override.rapid`、`override.spindle`、`velocity.max` | value 为比例或原生单位/秒 |
| `machine.touch-off`、`tool.touch-off` | axis、原生单位 value、system、target |
| `file.open` | 绝对 path |
| `file.save` | 绝对 path、text；服务写入后请求加载 |
| `tool.reload`、`tooltable.save` | 重载为空；保存传 text，路径从实际 INI 获取 |

动作的可用性由 capability 提示，条件始终由 Controller 校验。程序/刀具编辑文本最多 60,000 UTF-8 字节，并受整个 JSON 帧上限约束，超限拒绝，不截断内容；断线后不补写或重放。

Qt GUI 每 100 ms 发时间戳给 socket 工作线程。心跳超过 350 ms 时客户端请求停止点动，不再续租。服务租约标称 600 ms；由于原生 NML 命令可能持有 GIL 等待回执，此值不是硬实时停止上限。停止、退出、窗口失焦及界面释放都应取消本次点动；禁止将自动重连变成重新启动点动。

预览子进程使用临时参数/INI 副本、无 stdin，并设置解释及收集超时。它只能建立只读 stat 初始化 tooldata，不能建立 command/error channel。崩溃、解释错误、结果超限或不支持的执行扩展均作为显式错误传回，不伪造刀路。更多运行方法与未验收范围见 [Qt 迁移记录](qt-qml-migration.md)。


## 服务所有的 CAM 加工作业

当服务显式配置 `--cam-inbox` 时，`cam.job.start` 与 `cam.job.status` 可在不附着桌面会话的连接调用，均要求唯一的 `{transferId}` 参数。服务复用现有 Controller 和单一串行工作线程。新接口只接受 inbox 中校验通过的文件，不接受客户端路径或任意机床指令。具体状态、去重和联锁见 [CAM 协议](cam-link-protocol.md)。桌面会话与 CAM 作业可共用同一 Controller；桌面断开只取消桌面的预览、点动与未发送桌面操作，不取消服务已接受的 CAM 作业。服务停机仍取消未发送作业步骤，正在加工的程序不自动中止，重启不重放。


## CAM 与桌面共用点动控制器

`cam.jog.start` 接受 `{jogId,axis,direction,feedRate}`；`axis` 为 X/Y/Z，`direction` 为 ±1，`feedRate` 为 0–3000 mm/min 内的正数。`cam.jog.keepalive` 与 `cam.jog.stop` 接受 `{jogId}`。这三个方法不获取桌面 `session.attach` 所有权，仍只通过服务已有的同一个 Controller 串行执行；速度由服务根据最新机床长度单位换算。

一次点动绑定当前 Unix 连接与 UUID，独立租约为600毫秒；断开、停止或过期立即撤销，排队的旧开始不得执行。桌面状态心跳不能续租 CAM 点动。已有本地点动时拒绝远程开始；远程点动期间其他运动命令被拒绝，本地急停、断电、停止程序与停止点动可撤销远程租约。CAM 自动加工同样不得在点动租约内启动。重复 UUID 在五分钟保留窗口内拒绝，缓存最多4096条。桌面退出、服务关闭同样撤销点动；状态轮询、文件回执和已接受加工的归属保持原有规则。
