# CAM 联动 TCP 双向通信协议

CAM Link 使用一条完成协议握手的 TCP 长连接接收外部 CAM 生成的 G-code，同时回传接收回执、加工作业状态和只读机床反馈。外部协议版本为 2，帧头包含可读的消息类型，例如 `SEND_GCODE` 表示“发送加工文件”。外部 TCP 协议与设备内部的 Unix socket v2 控制协议独立。

## 模块职责

```text
app/cam-link/src/
  lib.rs                 系统服务公开入口
  cam_link/
    protocol.rs          CAM2 帧、严格 JSON、参数结构
    inbox.rs             分块收件、摘要、私有文件与原子回执
    control.rs           本地 v2 Unix 协议适配
    manual.rs            XYZ 点动及 450 ms 网络租约
    feedback.rs          状态查询、文件关联与串行发送
    discovery.rs         UDP 广播和握手
    session.rs           TCP 会话、请求分派及订阅
```

网络服务独立编译为 Rust 二进制，不嵌入 Python。LinuxCNC API、命令单写入者、联锁和作业持久化仍属于本地 Python Controller。启动器负责两者的启动顺序和保活。

## 启动

默认使用局域网直连，不传 `--token-file`、`--cert`、`--key`；CAM 发现设备后点击连接即可。第一帧仍是 `AUTH / session.auth`，参数为 `{}`，成功返回 `authenticated:true`，仅表示握手完成。直连不进行令牌认证或链路加密；协议、SHA-256、机床联锁和点动租约检查保留。后续令牌与 TLS 说明适用于显式配置的兼容模式，不会在认证失败后降级为直连。

从仓库根目录构建并安装全部模块：

```sh
cmake -S . -B build -DBUILD_TESTING=OFF -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build --parallel
sudo cmake --install build
betterlinuxcnc-launch --config ./launcher.json
```

构建需要 `app/cam-link/rust-toolchain.toml` 指定的 Rust 工具链。也可单独构建网络服务：`cargo build --manifest-path app/cam-link/Cargo.toml --release --locked`，二进制为 `app/cam-link/target/release/betterlinuxcnc-cam-link`。独立安装使用 `cmake -S app/cam-link -B build/services`，再 build/install。

安装后继续使用 `betterlinuxcnc-cam-link`，现有 `launcher.json` 的 `cam` 配置无需改名。CMake 默认构建并安装 Rust 二进制，覆盖旧 Python CLI，同时删除安装目录内旧 `bettercnc_cam_link` 包；Python wheel 不再安装这个命令。不再支持 `python -m bettercnc_cam_link`。`BETTERCNC_CAM_LINK_BINARY` 可指定为相同目标平台预构建的二进制。只做 Qt 测试可设 `BETTERCNC_BUILD_SYSTEM_SERVICES=OFF`；该选项不用于完整安装。

本地控制服务及启动器继续使用 Python；Rust 网络服务本身不需要 Python 运行时。

可选认证模式准备当前用户所有、权限为 0600 的令牌文件，内容为 32 至 256 个字母、数字、下划线或短横线，可通过 `secrets.token_urlsafe(32)` 生成。令牌不作为命令行参数直接传入。

```sh
betterlinuxcnc-cam-link \
  --host 127.0.0.1 --port 6522 \
  --inbox /home/cnc/cam-inbox \
  --token-file /home/cnc/.config/bettercnc/cam-token \
  --control-socket /run/user/1000/betterlinuxcnc/control.sock
```

默认只监听本机。跨设备连接时，将 `--host` 指定为机床设备的网络地址；如启用可选 TLS 模式，用 `--cert` 和 `--key` 提供证书和私钥，CAM 客户端验证证书后发送同样的 TCP 帧。该端口使用 CAM Link 自定义协议，不提供 HTTP 接口。

收件目录必须是当前用户所有的 0700 目录，不存在时创建。完整程序位于 `<inbox>/<transferId>/<filename>`，权限为 0600。未启用自动加工时，由本地操作员选择文件；开启后的行为见自动加工章节。

本地控制服务另行启动；它不可达时仍可接收程序，加工反馈返回 `controller_unavailable`。CAM Link 不启动 LinuxCNC 或控制服务。

## 不知道 IP 时发现机床

机床主动发送 UDP 广播，CAM 不需要预先配置机床 IP。发现功能默认关闭，服务增加以下参数后开启：

```sh
betterlinuxcnc-cam-link \
  --host 0.0.0.0 --port 6522 \
  --inbox /home/cnc/cam-inbox \
  --token-file /home/cnc/.config/bettercnc/cam-token \
  --control-socket /run/user/1000/betterlinuxcnc/control.sock \
  --discover \
  --device-id 550e8400-e29b-41d4-a716-446655440000 \
  --device-name CNC-01
```

`device-id` 使用安装时为该机床分配的稳定小写 UUID，每次启动沿用。上面的 UUID 为示例，多台机床必须分配不同 ID。默认局域网直连保持 `tls:false`，无需证书或密钥输入。仅既有部署显式配置时启用可选 TLS/令牌模式。

默认每三秒向 `255.255.255.255:8421` 广播，机床 UDP 监听端口也为 8421。CAM 监听本机 UDP `0.0.0.0:8421`，接收广播并保留 `recvfrom` 的源 IP、源 UDP 端口。IPv4 广播发送需启用 `SO_BROADCAST`；该广播地址覆盖本地网络段，不提供跨路由/VLAN 发现。[Linux ip(7)](https://man7.org/linux/man-pages/man7/ip.7.html)

可通过 `--discovery-address` 指定网卡所在子网的广播地址，`--discovery-port` 指定 CAM 监听端口，`--discovery-bind-port` 单独指定机床 UDP 绑定端口，`--discovery-interval` 调整广播间隔（0.1 至 60 秒）。多网卡时应显式选择机床 `--host` 地址及对应广播地址。CAM 和机床之间必须允许 UDP 发现端口、TCP 服务端口互通，交换机或无线客户端隔离不能阻断广播。

发现握手为：

```text
机床 -- UDP 广播 ANNOUNCE --> CAM
机床 <-- UDP 单播 DISCOVER_REPLY -- CAM
机床 -- UDP 单播 DISCOVER_ACK --> CAM
机床 <-- TCP 连接 + session.auth -- CAM
```

UDP 复用 24 字节 CAM2 帧头；一个数据报只能包含一帧，整帧最多 1024 字节，不拆包拼接，不传加工文件。三种帧头与正文事件严格匹配：

| 帧头类型 | 正文 event | 用途 |
| --- | --- | --- |
| `ANNOUNCE` | `discovery.announce` | 机床公布可连接的服务 |
| `DISCOVER_REPLY` | `discovery.reply` | CAM 回应刚收到的广播 |
| `DISCOVER_ACK` | `discovery.ack` | 机床确认收到 CAM 回复 |

广播正文如下，不包含认证令牌、程序或加工状态：

```json
{"version":2,"event":"discovery.announce","service":"bettercnc-cam-link","deviceId":"550e8400-e29b-41d4-a716-446655440000","deviceName":"CNC-01","tcpPort":6522,"tls":false,"nonce":"0123456789abcdef0123456789abcdef"}
```

CAM 将回复单播到广播报文的源 IP 和源 UDP 端口。回复复制 `deviceId`、`nonce`，并携带 CAM 自己的小写 UUID：

```json
{"version":2,"event":"discovery.reply","service":"bettercnc-cam-link","deviceId":"550e8400-e29b-41d4-a716-446655440000","camId":"3d813cbb-47fb-32ba-91df-831e1593ac29","nonce":"0123456789abcdef0123456789abcdef"}
```

机床仅接受与自身设备 ID 和近期广播随机数匹配的回复，确认帧将回复中的 `camId` 与 `nonce` 原样返回，并附带设备名、TCP 端口与 TLS 标记：

```json
{"version":2,"event":"discovery.ack","service":"bettercnc-cam-link","deviceId":"550e8400-e29b-41d4-a716-446655440000","deviceName":"CNC-01","camId":"3d813cbb-47fb-32ba-91df-831e1593ac29","tcpPort":6522,"tls":false,"nonce":"0123456789abcdef0123456789abcdef"}
```

CAM 根据确认报文的源 IP 和正文 `tcpPort` 建立 TCP 连接；确认中的设备 ID、CAM ID 和随机数应与待完成握手一致。IP 不从 JSON 中声明，不能用 `0.0.0.0` 或广播地址作为 TCP 目标。`tls` 描述服务监听配置，不替代 CAM 预设的 TLS 认证策略。

机床保留最近三个广播的随机数，每个有效期为三个广播间隔；过期、错误设备、格式错误和超长报文静默忽略。每秒最多确认八个有效回复；UDP 丢包或限流时，CAM 可等待下一次广播再握手。机床持续广播，可被多个 CAM 发现；完成发现不获取机床控制所有权，也不替代 TCP `session.auth`。关闭服务时停止广播并释放 UDP 端口。

CAM 客户端按上述帧格式编解码发现报文；服务通过 CLI 参数配置发现。真实跨设备广播仍须在部署的网卡、交换机和 CAM 客户端上联调。

## 帧格式

每帧为 24 字节固定帧头，随后是指定字节数的 UTF-8 JSON 正文：

```text
CAM2 | SEND_GCODE + NUL 补齐至 16 字节 | 正文长度 4 字节 | JSON 正文
```

| 字节偏移 | 长度 | 内容 |
| --- | --- | --- |
| 0 | 4 | ASCII 魔数 `CAM2`，标识外部 TCP 协议版本 2 |
| 4 | 16 | ASCII 消息类型，右侧用 NUL（0x00）补齐，禁止嵌入 NUL |
| 20 | 4 | 大端无符号整数，表示正文的字节数，不含帧头 |
| 24 | 1 至 65,536 | UTF-8 JSON 正文，其中 `version` 必须为 2 |

消息类型及含义如下：

| 帧头类型 | 含义 | 对应正文 |
| --- | --- | --- |
| `AUTH` | 连接认证 | `session.auth` |
| `PING` | 心跳 | `ping` |
| `JOG_START` | 开始连续点动 | `jog.start` |
| `JOG_KEEPALIVE` | 续租当前按住操作 | `jog.keepalive` |
| `JOG_STOP` | 停止本次点动 | `jog.stop` |
| `SEND_GCODE` | 发送加工文件 | `upload.begin`、`upload.chunk`、`upload.finish` |
| `ABORT_GCODE` | 取消当前文件接收 | `upload.abort` |
| `GET_RECEIPT` | 查询文件接收回执 | `upload.receipt` |
| `GET_STATUS` | 查询加工状态 | `status.get` |
| `SUB_STATUS` | 订阅加工状态 | `status.subscribe` |
| `UNSUB_STATUS` | 取消状态订阅 | `status.unsubscribe` |
| `REPLY` | 请求成功回执 | 带 `requestId`、`result` 的响应 |
| `ERROR` | 请求错误回执 | 带 `requestId`、`error` 的响应 |
| `STATUS` | 主动回传加工状态 | `machine.status` 事件，可能携带状态或错误 |
| `REQUEST` | 尚未支持的方法 | 其他 `method`，返回 `unsupported_method` |

接收端先校验魔数、类型和长度，再读取正文；帧头类型必须与正文 `method` 一致，不一致返回 `message_type_mismatch` 并关闭连接。上传的开始、分块和提交都标记为 `SEND_GCODE`，具体动作由正文 `method` 区分。回传端也使用同一帧头格式，可先根据类型区分回执、错误和主动状态。

TCP 拆包、粘包均按帧头中的长度处理。错误魔数、未知类型、非法长度、JSON 重复字段、非有限数、额外信封字段和非法版本会导致错误回执并关闭连接。原来仅含四字节长度的外部 TCP v1 帧不再接受，CAM 发送端必须同步升级；设备内部的 Unix socket 帧格式不变。

请求格式固定为：

```json
{"version":2,"requestId":"unique-id","method":"ping","params":{}}
```

`requestId` 为 1 至 64 个字符，在同一连接内不能复用。服务回执包含相同 `requestId`：

```json
{"version":2,"requestId":"unique-id","result":{"alive":true}}
```

失败返回 `error:{code,message}`，不包含 `result`。无法恢复请求 ID 时，错误回执使用空字符串 ID。业务参数错误通常允许继续通信；非法分块或提交失败会中止当前上传，并清理未发布文件。

认证前超时为 10 秒；帧正文读取和回传写入超时为 10 秒。认证后的请求空闲超时默认 60 秒，可用 `--idle-timeout` 调整；订阅推送不续期客户端请求空闲时间，CAM 应每 30 秒发送一次 `ping`。最多同时接纳四个连接；额外连接关闭。每个连接最多接收 100,000 个不同请求 ID，达到限制后需重连。

## 认证和方法

连接后第一条有效请求必须为：

```json
{"version":2,"requestId":"auth-1","method":"session.auth","params":{"token":"<token>"}}
```

成功返回 `authenticated:true`；未认证或令牌不符返回 `unauthorized` 后关闭连接。认证成功后可连续发送下列请求：

| 方法 | 参数 | 结果 |
| --- | --- | --- |
| `ping` | 空对象 | `alive:true` |
| `upload.begin` | `transferId`、`filename`、`size`、`sha256` | `state:"receiving"`、`nextOffset:0` |
| `upload.chunk` | `offset`、Base64 字符串 `data` | 下一块的 `nextOffset` |
| `upload.finish` | 空对象 | 完整接收回执，附 `duplicate` 布尔值 |
| `upload.abort` | 空对象 | `aborted:true`，清理当前未完成上传 |
| `upload.receipt` | `transferId` | 已发布的持久化接收回执 |
| `status.get` | 空对象 | 一次新鲜的加工状态 |
| `status.subscribe` | 秒数 `interval`，范围 1 至 60 | `subscribed:true`，随后开始推送 |
| `status.unsubscribe` | 空对象 | `subscribed:false`，停止本连接推送 |

每个连接同时只能有一个上传任务，期间可以查询或订阅状态。请求处理按接收顺序串行；推送在独立异步任务运行，与所有响应共用发送锁，保证帧字节不交错。客户端必须区分带 `requestId` 的响应与带 `event` 的推送，不能假设下一帧一定是刚发请求的响应。重复订阅会替换此前的订阅。

## 程序接收

`transferId` 由 CAM 生成，格式为带短横线的小写 UUID，重传沿用同一 ID。`filename` 为纯文件名：ASCII 字母、数字、下划线、短横线和点，以字母或数字开头，扩展名为小写 `.ngc`、`.nc` 或 `.gcode`，扩展名前最多 120 个字符。路径分隔符和 URL 编码不合法。

`size` 是完整文件的字节数，必须为正整数，默认上限为 64 MiB，可通过 `--max-bytes` 调整。`sha256` 为完整原始文件的 64 位小写十六进制摘要。文件必须是非空、不含 NUL 的 UTF-8 文本；G-code 语义仍由 LinuxCNC 解释器处理。

上传顺序为 `upload.begin`、若干 `upload.chunk`、`upload.finish`。分块的 `offset` 从 0 开始，必须等于上次响应的 `nextOffset`。每块解码后最多 32,768 字节，且不能超过声明的剩余文件大小。UTF-8 字符可以跨块，服务保留增量解码状态。

完整内容收到且摘要校验通过后，服务同步程序与回执，再原子发布接收目录。首次成功返回：

```json
{"version":2,"requestId":"finish-1","result":{"transferId":"550e8400-e29b-41d4-a716-446655440000","filename":"part.ngc","size":1234,"sha256":"<64 位摘要>","state":"received","duplicate":false}}
```

相同 ID、文件名、大小和摘要重新提交，返回相同回执及 `duplicate:true`；内容或名称冲突返回 `transfer_id_conflict`，不覆盖原程序。`upload.receipt` 的结果不含临时字段 `duplicate`。回执丢失时，先查询 `upload.receipt`；`unknown_transfer` 表示没有已发布回执，可按原 ID 重传完整文件。

连接中断、请求读取超时、显式中止、分块或摘要错误以及正常停机时，当前未完成文件会清理。断电或强制杀进程可能留下 `.receiving-*` 隐藏目录，管理员可在服务停机后清理；它们不会被作为完整程序发布。当前没有跨连接断点续传。已接收程序保留到本地人工清理，部署时需管理收件目录容量。

## 状态回传

订阅成功回执发送后，服务立即采样一次状态，然后按 `interval` 间隔重新采样并推送。采样通过独立的本地 Unix socket 连接调用只读 `machine.status`，不获取控制权、不续租点动、不消费 LinuxCNC 错误通道，也不要求桌面控制会话存在。

```json
{"version":2,"event":"machine.status","data":{"connected":true,"programState":"running","currentLine":12,"taskLine":100,"readLine":120,"progressPercent":null,"transferId":null}}
```

| 字段 | 含义 |
| --- | --- |
| `connected` | LinuxCNC 状态是否有效 |
| `programState` | `idle`、`running`、`paused`、`busy`、`estop`、`off` 或 `unknown` |
| `file` | LinuxCNC 当前程序的本地路径 |
| `transferId` | 程序路径位于当前 inbox 且与回执文件名一致时的传输 ID，否则 null |
| `currentLine` | LinuxCNC `motion_line`，运动执行行 |
| `taskLine` | LinuxCNC `current_line`，任务层执行行 |
| `readLine` | LinuxCNC `read_line`，解释器预读行 |
| `progressPercent` | 当前为 null，不根据行号估算完成比例 |
| `mode`、`powered`、`estop`、`paused` | 操作模式、电源、急停、暂停 |
| `queueDepth`、`activeQueueDepth` | 队列状态 |
| `tool`、`spindleSpeed`、`feedOverride`、`flood`、`mist` | 刀号、主轴命令转速 RPM、进给倍率、冷却状态 |

控制服务正常但 LinuxCNC 不可用时，状态为 `connected:false`、`programState:"unknown"`，行号和百分比为 null，其他字段可缺省。控制服务不可达或两秒内无法读取状态时，查询返回 `controller_unavailable`，订阅推送错误事件且不附带旧状态：

```json
{"version":2,"event":"machine.status","error":{"code":"controller_unavailable","message":"local controller status unavailable"}}
```

订阅继续重采样，连接恢复后重新推送实际状态。取消订阅后，已在网络缓冲区的事件仍可能先于取消回执到达；回执后不再产生该订阅的新事件。CAM 连接关闭时取消订阅，不影响机床加工。

`transferId` 只按本地路径关联收件，复制或本地编辑文件不构成新的作业记录。`received` 只表示完整接收，`idle` 只表示当前空闲，均不能证明加工成功。显式开启自动加工后，作业生命周期见下文；百分比、剩余时间、远程暂停及停止接口不在本次范围。


## 独立传输、独立回零与组合加工

2026-10-26 按用户最新要求拆分三种能力：`transfer.rs` 接收文件，`homing.rs` 请求独立回零，`wf-transhoming.rs` 请求回零后加工。原先 `upload.finish` 隐式自动加工的行为取消；即使传入 `--auto-run`，上传及查询接收回执也不调用控制服务、不触发运动。旧 CAM 客户端必须增加明确的启动请求，不能再把收到文件当作开始加工。

控制服务配置 `--cam-inbox`，Rust 网络服务的 `--auto-run` 现在仅允许显式启动请求。未启用时拒绝启动，但允许查询与取消既有作业。上传流程仍为 `upload.begin` → `upload.chunk` → `upload.finish`，保留大小、SHA-256、UTF-8 校验与原子发布；重复文件只返回接收回执。

| 外部方法 | 帧头 | 参数 | 结果 |
| --- | --- | --- | --- |
| `home.start` | `REQUEST` | `{operationId, clearanceConfirmed:true}` | `{job}`；只回零，不加载程序 |
| `home.status` / `home.cancel` | `REQUEST` | `{operationId}` | `{job}`；查询或取消指定回零 |
| `workflow.start` | `REQUEST` | `{transferId, clearanceConfirmed:true, machiningConfirmed:true}` | `{job}`；已接收文件校验 → 全部回零 → 加载 → 加工 |
| `workflow.status` / `workflow.cancel` | `REQUEST` | `{transferId}` | `{job}`；查询或取消组合任务 |
| `job.start` | `START_JOB` | `{transferId}` | `{job}`；已回零机床的单独加工入口，不自动回零 |
| `job.status` | `GET_JOB` | `{transferId}` | `{job}`；无执行记录时为 null |
| `job.cancel` | `REQUEST` | `{transferId}` | `{job}`；取消指定执行任务 |

`operationId` 和 `transferId` 是小写 UUID，区别于仅在当前连接去重的帧 `requestId`。独立回零记录在私有 inbox 的 `.homing/<operationId>.json`，不需要上传占位 G-code；程序意图仍记录在对应传输目录的 `execution.json`。同一编号不会再次执行；同一传输不能从单加工改成回零加工或反过来。重启后未完成意图为 unknown，不扫描补跑。

认证要求不变。本地 v2 方法为 `cam.home.start/status/cancel`、`cam.workflow.start`、`cam.job.start/status/cancel`；`workflow.status/cancel` 复用本地 job 接口。所有 native 调用由同一工作线程中的唯一 Controller 完成。Rust 不读取 HAL、不发送 MDI、不启停核心、不自动解除急停或使能。

组合请求先验证已接收文件、复制到只读 `.execution.ngc` 并持久化意图，然后按回执顺序切到手动/joint 模式，清除旧回零标志并确认，再执行 HOME ALL。只有全部 joint homed、无正在回零、解释器/运动队列空闲且 in-position，才能加载文件。随后确认正确文件、AUTO 模式，再发出一次 AUTO_RUN(0)。即使请求前已经回零，显式组合流程仍重新回零；希望复用当前回零结果时使用 `job.start`。

回零要求已连接、已使能、未急停、空闲、主轴停止、无限位覆盖、所有 joint 的回零配置有效。加工继续要求全部 joint 已回零、无硬限位、无覆盖且未启用 block delete。`clearanceConfirmed` 表示操作者确认当前刀具、工件及夹具条件下的整条回零路径无干涉；本机 Z 向下回零，先前空台无刀测试不能替代这个确认。`machiningConfirmed` 表示工件坐标系、刀具补偿与装夹已准备好；软件不会通过回零自动设定这些加工参数。

作业状态为 accepted、homing、loading、starting、running、completed、error、unknown。独立回零 completed 只代表回零确认，组合任务 completed 要求 AUTO_RUN 的 NML 序号确认 RCS_DONE 且运动完成。活动回零步骤最长等待 300 秒；超时只取消后续步骤并报告 unknown，不声称实体轴已经停止。取消请求向当前指定活动任务发送一次 abort，返回 unknown 并要求观察实际状态，不把“请求取消”冒充“停止完成”。不存在或已经结束的编号不停止其他运动。

错误、急停、掉电、状态丢失、外部命令写入、取消及服务退出均阻止未发送的加工步骤；结果不明禁止自动重试。被服务接受的任务不会因 CAM/桌面连接断开而撤销，服务本身关闭则不再续发。忙碌时拒绝新任务，不排队等待后来使能或空闲。对丢失响应，只查询 `home.status`/`workflow.status`/`job.status`。

## XYZ 持续点动

认证后的同一 TCP 连接可以发送以下操作。`jogId` 是新的小写 UUID；每次按住使用一个新编号，禁止重试或重放 `jog.start`。回执为 `{jogId,accepted:true}`，表示控制请求被接受，不代表实体轴已达到目标。

| 方法 | 参数 |
| --- | --- |
| `jog.start` | `jogId`、`axis`（X/Y/Z）、`direction`（整数 ±1）、`feedRate`（毫米/分钟，0 < 值 ≤ 3000） |
| `jog.keepalive` | 同一 `jogId`，仅续租，不能重新启动 |
| `jog.stop` | 同一 `jogId`，关闭本次拥有的控制会话 |

`manual` 能力通过公开 Unix 协议 `cam.jog.start/keepalive/stop` 复用服务当前 Controller，与 Qt 控制会话共存；其他点动正在运行时返回 `control_in_use`，不抢占运动。只接受已连接且实际处于 world 模式的 XYZ 轴，不猜测 joint 映射；毫米速度按最新 `linearUnits` 转为原生单位/秒，`increment=0`。Controller 仍根据最新状态检查回零、使能、急停、忙碌状态和 INI 速度上限，不自动回零、上电或运行程序。

CAM 按住时每 150 ms 左右续租；Rust 只有收到该连接的新续租请求才调用 `cam.jog.keepalive`，不自行后台续租。450 ms 未续租、TCP 断开、显式停止或服务关闭，会关闭本次 Unix 控制连接，撤销待发送步骤并停止本会话点动。控制服务还有独立的 600 ms 租约。超时后续租不能恢复点动，必须松开重新按住。软件租约不是硬实时停止保证：原生 LinuxCNC/NML 调用、操作系统调度等可能延迟处理；实体安全链不由网络租约替代。

浏览器按键松开、pointercancel、丢失捕获、失焦、页面隐藏、页面退出及组件卸载均撤销当前操作。旧机床服务会返回 `unsupported_method`，必须更新后才支持遥控，不能通过发送 MDI 或 G-code 绕过。


CAM 点动通过本地 `cam.jog.start/keepalive/stop` 接入服务的同一 Controller，不再附着或抢占桌面会话。网络断开关闭对应 Unix 连接，服务撤销该点动租约；桌面仍可读状态并优先执行急停或停止。独立网络450毫秒与服务600毫秒租约保持不变。
