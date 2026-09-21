**LinuxCNC 现代操作界面：架构调研与建议**

调研日期：2026-09-21。目标环境：用户指定 Debian 13、Intel 核显；LinuxCNC 小版本、CPU/核显代际、屏幕规格、驱动板及具体五轴结构尚未确定。

**结论：采用按功能划分的单体 Vue 前端，Tauri 作为可替换的桌面外壳，Python 作为唯一应用控制入口；机床状态、用户操作流程、三维渲染分别管理。**

推荐组合为 Vue 3、TypeScript、Vite、Pinia、局部使用 XState、Reka UI、Tailwind CSS、Three.js、Tauri 2，以及本地 Python/FastAPI 服务。技术名称只决定实现工具；架构的核心是命令所有权、状态真实性、模块依赖及进程生命周期。

本文区分官方事实、现有项目证据和针对本项目的工程建议。它不是穷尽互联网的文献综述，也没有在目标工控机上做性能或实机验证。涉及库版本和依赖，应在实施时锁定并复核。

**1. 哪些证据真正改变了设计**

| 核查结果 | 对本项目的影响 |
|---|---|
| LinuxCNC 的运动控制处在实时层，GUI 通过非实时接口提交命令 | Vue、Rust、Python 都不承担伺服闭环或加工插补 |
| LinuxCNC 错误队列消息被第一个读取者取走 | 由一个后台读取错误并分发；不能让多个 GUI 各自争读 |
| LinuxCNC 默认启动器在 DISPLAY 返回后执行清理 | 必须设计会话宿主，不能假设窗口和控制系统天然独立 |
| LinuxCNC 区分关节、坐标轴及多种运行状态 | 前后端协议不能只包含 XYZABC 和一个 running 布尔值 |
| Tauri 在 Linux 使用系统 WebKitGTK | 验收必须覆盖目标系统和核显，不能用 Chrome 测试替代 |
| 当前 Three.js WebGLRenderer 需要 WebGL 2 | 图形能力要实测，保留基础二维视图或关闭三维的路径 |
| 普通 WebSocket API 没有自动背压 | 状态流、事件、命令、几何数据要采用不同的缓冲策略 |

LinuxCNC 的层次结构及实时边界可见[官方架构说明](https://www.linuxcnc.org/docs/html/code/code-notes.html)。错误队列与坐标字段可见[2.9 Python 接口](https://linuxcnc.org/docs/2.9/html/config/python-interface.html)。生命周期行为核查了固定版本的[LinuxCNC v2.9.4 启动脚本](https://github.com/LinuxCNC/linuxcnc/blob/v2.9.4/scripts/linuxcnc.in#L907)。

**2. 架构方案比较**

| 方案 | 优点 | 本项目的代价 | 判断 |
|---|---|---|---|
| 全局 components / stores / api 按文件类型分类 | 起步快 | 修改点动要跨多个全局目录，业务边界薄弱 | 仅适合小原型 |
| 按功能分模块的单体应用 | 一个构建、统一发布、功能内聚、可检查依赖 | 要维护公开接口和模块责任 | 首选 |
| 完整 Feature-Sliced Design | 有层级、切片、公开 API 和跨层导入规范 | 机械套全套层级可能增加目录和归属争议 | 借鉴原则，不宣称完整采用 |
| 全面 Clean / Hexagonal 分层 | 外部依赖可替换，便于测试 | 每个按钮都套实体、仓储、用例会制造空壳 | 仅在通信、平台和时钟等真实边界使用 |
| 微前端 / Module Federation | 多团队可独立交付 | 多运行时、共享状态、版本组合及一致性验证更复杂 | 当前没有相应组织需求 |
| 大型运行时插件系统 | 可动态装配机型或扩展 | 增加权限、兼容、加载与生命周期管理 | 首版采用构建时模块和机型配置 |

FSD 官方强调公开边界、向下依赖，也明确无需创建全部层级；这支持采用较小的结构，而非照搬目录。[FSD 层级](https://fsd.how/docs/reference/layers/)、[公开 API](https://fsd.how/docs/reference/public-api/)。

微前端的独立交付优势与依赖重复、运行和组织成本，在原作者的[Micro Frontends](https://martinfowler.com/articles/micro-frontends.html)及[相关文献综述](https://arxiv.org/abs/2007.00293)中都有讨论。这里“不选微前端”是结合单机产品、统一控制状态与当前未提出多团队独立发布需求的判断，不是对所有项目的通用结论。

**3. 运行时边界与通信选择**

```text
Tauri 桌面窗口                         开发浏览器 / 后续只读客户端
      │                                          │
      └────────── 同一个 Vue 应用 ────────────────┘
                         │
               ControllerClient 公开接口
                         │
          本机 HTTP / WebSocket，鉴权与协议校验
                         │
             Python 本地控制服务（一个实例）
              ├─ 会话与操作权
              ├─ 命令生命周期
              ├─ LinuxCNC 接入所有者
              ├─ 状态采集、事件分发
              └─ 文件、应用记录
                         │
                 LinuxCNC / NML / HAL
                         │
                   实时运动与硬件

独立预览工作进程 ── 输出刀路几何 ── Vue 内独立渲染模块
```

首版直接由封装后的 Web 客户端连接回环地址上的 Python 服务。这样浏览器开发模式和 Tauri 使用同一协议，Rust 只承担窗口、文件对话框、应用启动信息等桌面能力。控制服务应校验会话身份和来源、限制可用命令；“只监听 localhost”本身不是鉴权。

不让 Rust 和 Python 各实现一套机床操作规则，也不默认让每条消息都多经过一次 JavaScript→Rust→Python 中转。只有明确要求“不开放本地 HTTP 端口”或需要进程级访问控制时，再换成 Tauri IPC→Rust→Unix socket→Python。替换仅发生在 ControllerClient 适配器内部。

Tauri 的权限限制管的是其 IPC 边界；直接调用本地 HTTP/WebSocket 的权限必须由 Python 服务自己校验，不能误以为会自动继承 Tauri capability。若使用 Rust 转发大量数据，优先评估有序流式 Channels；官方明确普通 Events 不为低延迟、高吞吐设计。[Tauri 安全边界](https://v2.tauri.app/security/)、[Channels 与 Events](https://v2.tauri.app/develop/calling-frontend/)。

FastAPI 是本地协议入口，不是实时控制器。第一版一个服务进程、一个 Uvicorn worker；LinuxCNC 对象归属于一个明确的执行上下文，避免在并发 HTTP 处理器中直接访问。控制器交互用有界调度及状态轮询；不能让一个长时间阻塞的命令等待占住停止请求的处理路径。预览计算另外开工作进程，不塞进 API 事件循环。

FastAPI 支持多 worker，但其内存通常不共享；对本项目，盲目增加 worker 会复制会话、操作权和设备连接状态。[FastAPI 部署模型](https://fastapi.tiangolo.com/deployment/concepts/)。如果以后确需扩大 API 层，保持机床接入所有者唯一，再增加面向客户端的进程。

“唯一应用控制入口”约束的是本软件体系，不会自动阻止 AXIS、halui 或实体手轮从其他通道操作。必须在机床集成中统一规定各控制来源的启用条件；前端操作权不能冒充全机控制权。

**4. 前端模块结构**

以下为建议目录，尚未创建项目或安装依赖。

```text
src/
├── app/                         # 启动、装配、路由、全局布局
├── pages/                       # 加工、准备、程序、工具、诊断页面
├── packages/
│   ├── ui-system/               # Reka 包装组件与设计主题
│   ├── controller-session/      # 状态投影、操作门面、连接与回执
│   ├── protocol/                # 自动生成的协议类型和校验入口
│   ├── desktop-platform/        # Tauri 原生功能及浏览器替代实现
│   ├── manual-control/          # 点动、输入所有权、步距设置
│   ├── machining/               # 程序运行与作业流程展示
│   ├── programs/                # 程序库、编辑草稿、加载
│   ├── tooling/                 # 刀具与对刀流程界面
│   ├── diagnostics/             # 报警、事件、连接诊断
│   └── toolpath-view/           # 三维/二维预览、拾取、资源回收
└── styles/                      # 主题接入和极少量全局样式
```

这里的 packages 是源代码中的平级模块，不代表都要发布 npm 包。页面专用的小块 UI、搜索条件等可以留在 pages；会触发机床动作的流程进入对应功能模块。普通 HTTP 封装留在 controller-session 私有目录，首版无需为了“分层”再创建一个只有转发功能的 connection 包。

每个模块的直接根文件为公开入口，子目录为私有实现。例如：

```text
controller-session/
├── index.ts                    # 少量常用公开能力
├── client.ts                   # 客户端工厂与稳定操作接口
├── model.ts                    # 对外状态模型
├── vue.ts                      # Vue 注入与只读订阅入口
├── lib/                        # 协议映射、连接、回执、私有 store
└── tests/                      # 通过公开接口测试
```

依赖方向如下，使用矩阵落到自动检查：

| 调用方 | 可以依赖 | 不应该依赖 |
|---|---|---|
| app | 页面、各模块公开入口 | 模块 lib 内部 |
| pages | 功能模块、ui-system、会话公开入口 | WebSocket、底层 Tauri API |
| manual-control / machining / tooling 等 | controller-session、ui-system，必要时 desktop-platform | 其他业务模块的私有 store；相互形成循环 |
| controller-session | protocol、Vue/Pinia 等自己的实现依赖 | 页面、具体加工面板、Three.js |
| toolpath-view | 明确的几何/姿态输入、自己的渲染实现 | 启动加工、回零、点动命令 |
| ui-system | Reka、Vue、主题 | LinuxCNC 状态和机床命令 |
| desktop-platform | Tauri 及自身接口 | 页面与机床业务 |

app 创建一个控制会话并注入实际或模拟适配器，避免每个页面各连一次设备。模拟模式必须明显标识，产品运行配置不能因连接失败自动切换为假机床。

跨模块仅引用公开入口，类型引用也遵守相同规则。使用 dependency-cruiser 检查越界引用、反向依赖、循环，以及生产代码引用 tests。测试可以使用本模块 fixtures，但只通过公开接口触发被测行为。[dependency-cruiser](https://github.com/sverweij/dependency-cruiser)。

**5. 状态模型：四个不同的所有者**

| 数据 | 所有者 | 更新方式 |
|---|---|---|
| 实际坐标、模式、关节回零、主轴、运动状态 | LinuxCNC；后台采集 | 前端仅根据服务端快照投影 |
| 控制会话、命令回执、允许操作及拒绝原因 | Python 控制服务 | 服务端事件/快照 |
| 用户正在进行的连接、点动交互、对刀向导步骤 | 对应功能状态机 | 明确事件驱动 |
| 页面布局、主题、筛选、未提交表单草稿 | Vue 局部状态或 Pinia | 本地交互，可按需持久化 |

Pinia 是跨组件共享状态的实现工具；实际机床状态、交互状态机和渲染对象不应都挤进一个全局 machineStore。状态快照只暴露只读访问和派生查询，写入口留在 controller-session 内部。[Pinia 官方核心概念](https://pinia.vuejs.org/core-concepts/)。

不要只设计一个“离线/空闲/运行/报警”的万能枚举。连接状态、机床上电/急停状态、MANUAL/MDI/AUTO 模式、解释器状态、运动状态、关节回零状态、控制权是独立维度。界面可用派生值展示人能理解的总结，但保留底层区别。

五轴协议从第一天区分 joint 与 axis、工件坐标与机床坐标、指令位置与反馈位置、毫米与角度，以及坐标是否有效。程序正在读取的行与实际运动相关的行也应分开。具体字段根据安装版本和运动学组件核对；不能把一组 XYZ 值标成没有条件的“真实刀尖坐标”。

建议后台返回每个操作当前是否可用及原因，前端据此解释“为何不能启动”；命令到达时后台再次检查，因为显示与点击之间状态可能改变。

**6. 使用局部状态机，不在前端复制 CNC 控制器**

Vue 官方承认状态机适合复杂状态流，并提供外部状态系统集成说明；XState 有 Vue 适配。[Vue 状态机说明](https://vuejs.org/guide/extras/reactivity-in-depth.html#state-machines)、[XState Vue](https://stately.ai/docs/xstate-vue)。

本项目建议把状态机用于以下流程，而非每个弹窗：

| 流程 | 示例状态 | 价值 |
|---|---|---|
| 控制会话 | 未连接 → 连接中 → 同步中 → 可操作 → 数据过期/断线 | 防止 socket 一连上就开放按钮 |
| 一次命令 | 提交中 → 已受理 → 已下发 → 等待后置状态 → 已完成/拒绝/结果未知 | 区分发出请求和动作达成 |
| 点动交互 | 未按住 → 请求中 → 按住运行 → 停止中 → 已释放/失效 | 明确每种输入结束路径 |
| 对刀向导 | 填写参数 → 校验 → 请求执行 → 观察结果 → 保存/失败 | 避免多个布尔变量组合失控 |

XState 管用户交互进度，不预测实际轴位置。需要在界面关闭后仍有确定行为的多步控制程序，应由后台或经过验证的 LinuxCNC 程序负责；前端向导只跟踪操作标识。

**7. 命令与数据流协议**

建议为每个连接携带服务实例标识、机床会话标识、协议版本和状态序号。首版优先发送小型完整状态快照；在实测证明带宽/CPU 有压力后才引入增量，增量必须带基准序号且能恢复完整快照。

连接存活与设备状态新鲜度分别判断：WebSocket 仍能收发心跳，不代表 LinuxCNC 数据还在更新。服务端报告采集健康和数据年龄，客户端用本地单调时钟追踪接收间隔；避免直接拿两端未同步的墙上时钟相减来判断是否过期。服务实例变化或状态序列缺口触发重新同步。

一次动作使用独立请求 ID。生命周期示例：

```text
用户点击启动
  → 客户端提交请求 ID、目标程序版本、当前会话
  → 服务端检查操作权与机床状态
  → 请求已受理
  → 下发给 LinuxCNC
  → 观察命令回执和操作对应的状态条件
  → 报告动作结果
```

“HTTP 成功”“NML 命令处理完成”“机床已经停止/到位”“整个加工程序结束”是不同含义。超时可能表示结果未知，不能自动判定没执行，再无条件重发。去重记录只在定义好的会话/保留范围内提供作用；服务崩溃跨越物理动作时，不应宣称能保证严格 exactly-once。

重连时先撤销旧操作会话并重新同步；界面不会自动重放回零、MDI、启动、继续、点动等动作。前端重连自动化仅负责恢复通信，不能把自动恢复通信变成自动恢复运动。

| 消息类型 | 推荐通道与处理 |
|---|---|
| 操作命令、受理结果、完成结果 | WebSocket 控制消息；有界排队，明确 ID 与结果 |
| 坐标和连续状态 | WebSocket 状态流；过载时合并快照，保留最新状态 |
| 报警和操作事件 | 有编号、可补取的事件记录；不能像坐标一样随意覆盖 |
| 程序文件、预览几何 | HTTP 上传/下载，按需分块；不挤占控制消息流 |
| UI 布局与主题 | 本地状态，不向 LinuxCNC 发送 |

控制、状态、文件是逻辑分类；首版不必为每种小消息开一个 socket。大文件/几何走独立 HTTP 数据路径，若实测控制通道仍受遥测拥堵影响，再分离连接。已经进入网络发送队列的大消息不能靠应用内“高优先级”直接插队，因此要从源头限制队列和报文大小。[WebSocket 背压限制](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)、[发送缓冲](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/bufferedAmount)。

协议从一套明确 schema 生成客户端类型。HTTP 可用 FastAPI 的 OpenAPI 生成客户端；WebSocket 报文需要单独声明并校验，不能以为 HTTP 的 OpenAPI 会自动覆盖所有流消息。TypeScript 类型不能代替入站运行时校验。[FastAPI 客户端生成](https://fastapi.tiangolo.com/advanced/generate-clients/)、[TypeScript 类型擦除](https://www.typescriptlang.org/docs/handbook/2/classes)。

**8. 连续点动与故障路径**

点动是架构验证的优先场景。点动模块统一处理 pointerup、pointercancel、失去捕获、失焦、隐藏、路由离开等，输入框聚焦时不让全局快捷键误触发运动。不能只监听鼠标松开；触摸输入可能被取消。[pointercancel](https://developer.mozilla.org/en-US/docs/Web/API/Element/pointercancel_event)、[页面可见性](https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API)。

前端的结束事件只是第一层。连续点动需要定义有限有效期的操作授权和后台超时处理：当前授权撤销或续期停止时，后台结束该点动。后台超时使用单调时钟，参数依据机床速度、制动距离、输入方式及允许响应时间确定，不给一个适用于所有机床的固定毫秒数。

每次按住对应独立的操作代次，释放后立即使该代次失效；迟到的启动回执、启动请求或续期不能恢复它。停止/撤销不能排在长任务或大文件后等待，后台撤销授权时同时拒绝尚未下发的同代次启动。这里需要专门验证“按下后立即松开、启动确认后到”的竞态。

单纯 Python 心跳无法覆盖 Python 自己卡死或退出，因此还要在机床侧配置并验证适合该设备的失联处置及独立的急停/使能链。实体按钮和手轮的控制来源也要纳入。此处是待实现的集成要求，不是 LinuxCNC 默认自带的网页点动保护。

| 故障 | 应定义的行为 |
|---|---|
| 点动期间窗口失焦 | 当前点动结束，恢复焦点后不自动恢复 |
| WebView 卡住、心跳停止 | 后台授权到期结束点动 |
| 控制服务停止响应 | 机床侧失联机制接管，而不是等待网页发送停止 |
| 三维加载失败 | 预览显示不可用，其他状态与操作流程保持可诊断 |
| 自动加工时界面断线 | 按机床工艺确定暂停/其他处置；不能套用点动逻辑，也不默认承诺继续 |
| 控制服务重启 | 重新绑定机床会话、只读同步，不重发未确认动作 |

**9. 必须单独设计 LinuxCNC 会话生命周期**

固定版本启动脚本会在前台 DISPLAY 程序结束后运行 Cleanup，并停止相关进程、实时线程和 HAL。这是进程拓扑必须考虑的事实。[v2.9.4 启动与清理源码](https://github.com/LinuxCNC/linuxcnc/blob/v2.9.4/scripts/linuxcnc.in#L907)。

因此，若产品要求“重启界面而不重建 LinuxCNC 会话”，推荐设计一个长期运行的会话宿主作为 DISPLAY 入口，由它管理受控的界面启动/关闭及退出请求。Python 控制服务独立于 WebView，但其启动参数、用户权限和生命周期绑定到指定机床会话。systemd 可以负责相关服务监督，但不能仅通过 Restart=always 实现任意故障后的安全恢复。

会话宿主只负责生命周期协调，不再成为第二个机床命令源。可以将少量宿主职责并入 Python 服务的启动器，避免多造一套完整服务。正常退出、界面崩溃、宿主崩溃、控制器退出必须分别在仿真环境验证。若首版接受关闭界面就结束控制会话，也要明确采用这个策略，不宣称支持独立恢复。

**10. 五轴预览与核显性能**

Three.js 是渲染库，不是 LinuxCNC 解释器或 CAM。建议用隔离的预览工作进程，基于匹配的 LinuxCNC 解释器及机型配置生成几何，前端负责显示。预览输入要记录程序内容标识、坐标/刀具相关配置版本，以及影响解释的依赖；任一变化都可能要求使预览失效。

LinuxCNC 官方明确区分执行解释器和预览解释器。探测结果等运行时信息在预览时未知，自定义 remap 也必须考虑预览模式，所以不能承诺任意程序都能生成完全等价的事前路径。[预览与 Remap](https://www.linuxcnc.org/docs/2.9/html/remap/remap.html#_axis_preview_and_remapped_code_execution)。

预览应区分：程序计划路径、采样得到的运行轨迹、机床姿态示意。采样轨迹并不是完整伺服轨迹。碰撞检测是另一个需要真实几何、运动学与误差边界的功能，不能用模型动画冒充。

在 Vue 中，大型不可变刀路数据放在普通结构或 shallowRef 中；Three.js 场景、材质和缓冲留在渲染器内部，不进入深度响应式 Pinia 树。Vue 官方说明深度响应式在巨大嵌套数据上存在开销。[Vue 性能指导](https://vuejs.org/guide/best-practices/performance.html)。

建议渲染策略：

- 按块合并线段和几何，避免每条 G1 创建一个独立对象。
- 单独保留小规模实时轨迹，设定容量和清理机制。
- 解码与几何准备可以放 Web Worker；GPU 渲染是否移到 OffscreenCanvas 再按 WebKitGTK 支持和收益决定。
- 静止时按需重绘；运行和拖动时限制帧率与像素比，不让后台持续满帧消耗核显。
- 首版提供基本的二维路径/禁用三维模式，图形异常应能定位和恢复。
- 曲线离散和模型简化记录精度，用于显示的简化不得改变执行程序。

当前 Three.js WebGLRenderer 依赖 WebGL 2。[Three.js 文档](https://threejs.org/docs/pages/WebGLRenderer.html)。Tauri 官方记录了 WebKitGTK 的图形异常和可能静默使用慢路径的问题；创建上下文成功不足以证明性能合格。[Tauri Linux 图形说明](https://v2.tauri.app/develop/debug/linux-graphics/)。

Intel 核显不是一个统一性能等级。要记录 CPU 型号、核显代际、RAM、内核、Mesa、WebKitGTK、X11/Wayland、屏幕分辨率与缩放。Debian 13 提供所需 WebKitGTK 包，说明依赖可获得，不等于所有这些组合均已通过测试。[Debian 13 WebKitGTK 包](https://packages.debian.org/trixie/libwebkit2gtk-4.1-0)。

**11. Apple 风格如何落实到代码**

Reka 提供无默认视觉约束的交互基础；Tailwind 提供工具类和主题变量。集中定义语义设计变量，例如背景、面板、文字层级、分隔线、选中、警告、故障，再由 ui-system 的组件使用，禁止在业务页面重复创造略有差异的按钮样式。[Reka](https://reka-ui.com/docs/overview/introduction)、[Tailwind 主题变量](https://tailwindcss.com/docs/theme)。

建议界面采用固定的主要操作区域、克制的颜色、清晰的数字与充分留白。轻量阴影和局部过渡即可表达层级；大量实时背景模糊、透明叠层和持续动画应根据核显实测决定。重要状态不只靠颜色，操作确认不隐藏在动画完成之后。

普通按钮、输入框可以复用 Reka 交互基础；“按住点动”需要自定义输入生命周期，不能当成普通 click 按钮。物理量组件需要单位、精度、上下限与无效状态，这些是机床产品要求，不是通用组件库自动提供的。

Tailwind v4 的新浏览器能力要求在目标 WebKitGTK 上验证；不要仅凭 Safari 的版本数字机械等同判断 Linux WebKitGTK。[Tailwind 兼容性](https://tailwindcss.com/docs/compatibility)。字体与图标随应用本地提供，离线不依赖 CDN。

**12. 部署、版本与测试**

针对固定 Debian 13 设备，首选 .deb 和明确的系统依赖，Python 使用能正确导入发行版 LinuxCNC 扩展的环境；不要假设随便换一个 Python 解释器就能加载系统扩展。Tauri 官方支持 Debian 打包。[Tauri Debian 打包](https://v2.tauri.app/distribute/debian/)。

前端、后台和协议记录兼容版本；不兼容时可诊断地拒绝控制。UI 和后台升级在机床维护流程中进行，数据库变更与回滚一起设计。SQLite 只保存应用偏好、操作/报警记录和附加元数据；不作为实际坐标、当前模式或刀表权威来源。已有 LinuxCNC 刀表或工具数据库仍由其所属系统管理。

| 测试层 | 要验证什么 |
|---|---|
| Vitest / 模块测试 | 状态转换、无效操作、断线、不重发、超时未知、单位和坐标展示 |
| Vue 组件与浏览器流程测试 | 禁用原因、键盘/触摸、草稿、页面切换 |
| 协议与 Python 集成测试 | Schema、旧会话拒绝、命令关联、唯一错误读取、重启恢复 |
| LinuxCNC 仿真配置 | 回零、模式、暂停、五轴坐标、刀补、remap、程序状态 |
| Tauri Linux 应用测试 | 真正的 WebKitGTK、窗口焦点、退出、全屏与缩放 |
| 目标机故障与负载试验 | 服务/窗口退出、图形失败、长期运行、实时线程抖动 |

浏览器测试不能完全替代 Tauri 测试。当前 Tauri 官方推荐 WebdriverIO 及其 Tauri 服务，并说明原生驱动路径；实施时固定相容版本。[Tauri WebDriver](https://v2.tauri.app/develop/tests/webdriver/)。Vue 官方区分单元、组件和端到端测试。[Vue 测试](https://vuejs.org/guide/scaling-up/testing.html)。

性能验收先准备代表性的实际程序，再增加大数据压力案例；记录加载时间、输入反馈分位数、渲染帧时间、内存增长、后台事件延迟和实时线程最大抖动。界面采样/刷新频率从低负载基线开始，按测量调整，不声称越高越好。

LinuxCNC 官方要求在延迟测试期间施加图形、磁盘等负载，并说明不要同时运行 LinuxCNC 或 StepConf。因此要将“独立实时延迟测试＋渲染负载”和“运行中的仿真/实机验证”分成两套试验。[LinuxCNC 延迟测试](https://linuxcnc.org/docs/devel/html/en/install/latency-test.html)。

**13. 现有开源项目能借鉴什么**

| 项目 | 本次核查到的材料 | 可借鉴 | 不能据此推断 |
|---|---|---|---|
| LinuxCNC AXIS / QtVCP | 官方接口、组件说明与启动源码 | 命令前置条件、运行状态、生命周期、预览语义 | 换一套 CSS 就能复用全部机床交互 |
| QtPyVCP | Status 插件源码 | 集中采集状态，通过数据通道通知 UI | 它与 QtVCP 是同一个框架 |
| lcncgui | 仓库 README 与作者项目说明 | Python 后台＋WebSocket＋Web 前端确有实践 | 已证明适合本机五轴、已完成故障验证 |
| LinuxCNC_UI | README 中明确列出的测试环境 | 较早的 Web 控制界面思路 | LinuxCNC 2.7 / Python 2 环境的经验可直接搬到 Debian 13 |

QtPyVCP 的[Status 源码](https://www.qtpyvcp.com/_modules/qtpyvcp/plugins/status.html)展示了集中状态轮询与通知。它是独立于 QtVCP 的项目，这里只是比较架构。

[lcncgui 仓库](https://github.com/salomom/lcncgui)说明使用 Python/LinuxCNC 与 WebSocket，并提供 Web 界面；本次没有对其全代码和实机行为做审计。[LinuxCNC_UI](https://github.com/MikhailBerezhanov/LinuxCNC_UI)的 README 列出 LinuxCNC 2.7、旧 Debian 和 Python 2 环境，应作为历史参考。项目存在证明路线可行，不等于可以直接作为生产底座。

**14. 建议实施顺序与改变方案的条件**

第一步：在目标 Debian 13 / Intel 核显上验证 Tauri、Tailwind、实际规模的 Three.js 刀路与输入响应，另做实时延迟负载测试。通过后锁定硬件/系统基线；若 WebKitGTK 的性能或稳定性未达目标，保持 Vue 业务模块不动，比较 Chromium 承载路径。

第二步：确定机床协议和会话生命周期，做只读状态、单一报警读取及模拟适配器。首先验证通信断开时界面会正确标记状态失效。

第三步：完成有后置条件的命令流程、模式切换和点动失效路径，在仿真中覆盖 UI、服务及会话退出。此阶段才进入真实动作接入。

第四步：扩展对刀、工具、程序管理和五轴预览，对实际机床配置逐项验证，完成视觉统一。

第五步：根据真实需求扩展只读远程查看；远程控制、多控制端接管和运行时插件另立决策，不自动沿用本机操作假设。

只有出现多个独立团队且确实需要独立部署时再评估微前端；只有复杂操作流程增长时才扩大状态机范围；只有基准测试证明需要时才引入额外数据通道、二进制格式或更多后台进程。

**当前仍需确认的实施输入**：实际 LinuxCNC 版本与安装源、CPU/核显代际、显示会话、屏幕规格、机床轴/关节拓扑、控制板类型、主操作输入方式，以及自动加工遇到 UI 失联时要求的工艺行为。这些不妨碍选定模块架构，但会影响协议字段、点动实现和验收条件。
