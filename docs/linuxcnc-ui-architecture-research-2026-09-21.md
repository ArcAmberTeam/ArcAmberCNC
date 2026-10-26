**Modern LinuxCNC operator UI: architecture research and recommendations**

> Decision update, 2026-09-22: the user selected Tauri-only product operation. The [Tauri-specific control architecture](tauri-local-control-architecture.md) supersedes this document's recommendations for direct browser connections, HTTP/WebSocket control gateways, FastAPI, and replaceable desktop environments. This remains a historical research record; implementation follows root rules and newer architecture decisions.

Research date: 2026-09-21. Target: user-specified Debian 13 and Intel integrated graphics. LinuxCNC minor version, CPU/GPU generation, display specifications, driver board, and specific five-axis geometry were not yet determined.

**Conclusion: use a feature-organized monolithic Vue frontend, Tauri as a replaceable desktop shell, and Python as the sole application control entry; manage machine state, user workflows, and 3D rendering separately.**

Recommended stack: Vue 3, TypeScript, Vite, Pinia, selective XState, Reka UI, Tailwind CSS, Three.js, Tauri 2, and a local Python/FastAPI service. These names identify implementation tools; architecture centers on command ownership, truthful state, module dependencies, and process lifecycles.

This document distinguishes official facts, existing-project evidence, and engineering recommendations for this project. It is neither an exhaustive literature review nor a performance/hardware validation on the target industrial PC. Pin and recheck library versions/dependencies during implementation.

**1. Evidence that changed the design**

| Finding | Project implication |
|---|---|
| LinuxCNC motion runs in the real-time layer; GUI submits through non-real-time interfaces | Vue, Rust, and Python do not run servo loops or machining interpolation |
| The first reader removes messages from LinuxCNC's error queue | One backend reads/distributes errors; GUIs must not compete |
| Default LinuxCNC launcher cleans up after DISPLAY returns | Design a session host; window/control independence is not automatic |
| LinuxCNC distinguishes joints, axes, and multiple operating states | Protocol needs more than XYZABC and one running boolean |
| Tauri uses system WebKitGTK on Linux | Accept on target OS/GPU; Chrome tests cannot substitute |
| Current Three.js WebGLRenderer requires WebGL 2 | Measure graphics support; retain basic 2D/disable-3D paths |
| Ordinary WebSocket API has no automatic backpressure | State, events, commands, and geometry need different buffering |

See [official LinuxCNC architecture](https://www.linuxcnc.org/docs/html/code/code-notes.html) for layers/real-time boundaries and [2.9 Python interface](https://linuxcnc.org/docs/2.9/html/config/python-interface.html) for error queues/coordinate fields. Lifecycle behavior was checked against pinned [v2.9.4 startup source](https://github.com/LinuxCNC/linuxcnc/blob/v2.9.4/scripts/linuxcnc.in#L907).

**2. Architecture comparison**

| Approach | Benefits | Project cost | Assessment |
|---|---|---|---|
| Global components / stores / api by file type | Fast start | Jogging changes span global directories; weak domain boundaries | Small prototypes only |
| Feature-modular monolith | One build/release, cohesive features, checkable dependencies | Maintain public interfaces/ownership | Preferred |
| Full Feature-Sliced Design | Layers, slices, public APIs, import rules | Mechanical layering adds directories/ownership disputes | Borrow principles, not claim full adoption |
| Full Clean / Hexagonal layering | Replaceable dependencies, testability | Entity/repository/use-case wrappers for every button create empty shells | Use at real transport/platform/clock boundaries |
| Microfrontends / Module Federation | Independent team delivery | Multiple runtimes, shared state, version combinations, consistency cost | No current organizational need |
| Large runtime plugin system | Dynamic machine/extension assembly | Permissions, compatibility, loading, lifecycle complexity | Build-time modules/machine configuration initially |

FSD emphasizes public boundaries/downward dependencies and explicitly does not require every layer. This supports a smaller structure, not copied directory trees. [FSD layers](https://fsd.how/docs/reference/layers/), [public API](https://fsd.how/docs/reference/public-api/).

Independent-delivery benefits and dependency/runtime/organizational costs are discussed in [Micro Frontends](https://martinfowler.com/articles/micro-frontends.html) and a [literature review](https://arxiv.org/abs/2007.00293). Rejecting microfrontends here reflects a single-machine product, unified control state, and no stated multi-team independent-release need, not a universal judgment.

**3. Runtime boundaries and communication**

```text
Tauri desktop window                    Development browser / future read-only client
      │                                          │
      └──────────── Same Vue application ────────┘
                         │
               Public ControllerClient interface
                         │
          Local HTTP / WebSocket, authentication and validation
                         │
             Local Python controller service (one instance)
              ├─ Sessions and control ownership
              ├─ Command lifecycle
              ├─ LinuxCNC access ownership
              ├─ State collection and event distribution
              └─ Files and application records
                         │
                 LinuxCNC / NML / HAL
                         │
                 Real-time motion and hardware

Independent preview worker ── Toolpath geometry ── Separate Vue rendering module
```

Initially, an encapsulated Web client connects directly to loopback Python. Browser development and Tauri then use one protocol; Rust owns only windows, file dialogs, startup information, and other desktop capabilities. The service validates session identity/origin and allowed commands; listening only on localhost is not authentication.

Do not duplicate machine rules in Rust/Python or automatically route every message JavaScript→Rust→Python. Switch to Tauri IPC→Rust→Unix socket→Python only for explicit no-local-HTTP requirements or process-level access control, inside ControllerClient's adapter.

Tauri permissions protect its IPC boundary; Python must validate direct HTTP/WebSocket independently rather than assuming inherited Tauri capabilities. For large Rust-forwarded data, evaluate ordered streaming Channels; ordinary Events are explicitly not designed for low latency/high throughput. [Tauri security](https://v2.tauri.app/security/), [Channels and Events](https://v2.tauri.app/develop/calling-frontend/).

FastAPI is a local protocol entry, not a real-time controller. Start with one service process/one Uvicorn worker. LinuxCNC objects belong to one explicit execution context, not concurrent HTTP handlers. Use bounded scheduling/status polling; long blocking acknowledgements must not monopolize stop handling. Preview computation belongs in separate processes, not the API event loop.

FastAPI supports workers, but their memory is generally not shared. Blindly adding workers duplicates sessions, ownership, and device state. [Deployment model](https://fastapi.tiangolo.com/deployment/concepts/). Future API scaling must retain one machine-access owner before adding client-facing processes.

“Sole application control entry” constrains this software, not AXIS, halui, or physical handwheels on other channels. Define enable conditions for all control sources during integration; frontend ownership is not whole-machine ownership.

**4. Frontend modules**

Proposed structure; no project/dependencies had yet been created:

```text
src/
├── app/                         # Startup, composition, routing, global layout
├── pages/                       # Machining, preparation, programs, tools, diagnostics
├── packages/
│   ├── ui-system/               # Reka wrappers and design theme
│   ├── controller-session/      # State projection, operations, connection, receipts
│   ├── protocol/                # Generated types and validation entry
│   ├── desktop-platform/        # Tauri native functions and browser alternatives
│   ├── manual-control/          # Jogging, input ownership, increments
│   ├── machining/               # Program execution and workflow presentation
│   ├── programs/                # Library, edit drafts, loading
│   ├── tooling/                 # Tool and touch-off workflow UI
│   ├── diagnostics/             # Alarms, events, connectivity diagnostics
│   └── toolpath-view/           # 3D/2D previews, picking, resource cleanup
└── styles/                      # Theme integration and minimal global styles
```

packages are sibling source modules, not necessarily published npm packages. Page-specific UI/search state may remain in pages; machine-action workflows belong in feature modules. HTTP wrappers stay private in controller-session; avoid a forwarding-only connection package just for layering.

Direct module-root files are public entries; subdirectories are private. Example:

```text
controller-session/
├── index.ts                    # Small common public surface
├── client.ts                   # Client factory and stable operations
├── model.ts                    # Public state model
├── vue.ts                      # Vue injection/read-only subscriptions
├── lib/                        # Mapping, connection, receipts, private store
└── tests/                      # Public-interface tests
```

Enforce this dependency matrix automatically:

| Caller | May depend on | Must not depend on |
|---|---|---|
| app | Pages/module public entries | Module lib internals |
| pages | Features, ui-system, public session API | WebSocket, low-level Tauri APIs |
| manual-control / machining / tooling | controller-session, ui-system, desktop-platform as needed | Other feature private stores or cycles |
| controller-session | protocol and its own Vue/Pinia implementation dependencies | Pages, machining panels, Three.js |
| toolpath-view | Explicit geometry/pose input and own renderer | Start/home/jog commands |
| ui-system | Reka, Vue, theme | LinuxCNC state/commands |
| desktop-platform | Tauri and its own interfaces | Pages/machine business logic |

app creates one control session and injects real/simulated adapters, rather than connecting each page separately. Clearly label simulation; production must never switch to a fake machine after connection failure.

Cross-module imports, including types, use public entries only. dependency-cruiser checks boundary violations, reverse dependencies, cycles, and production imports of tests. Tests may use local fixtures but invoke behavior through public APIs. [dependency-cruiser](https://github.com/sverweij/dependency-cruiser).

**5. State: four owners**

| Data | Owner | Update mechanism |
|---|---|---|
| Actual coordinates, mode, joint homing, spindle, motion | LinuxCNC, collected by backend | Frontend projects server snapshots only |
| Control session, receipts, permitted operations/reasons | Python service | Server events/snapshots |
| Connection/jog interactions, touch-off wizard steps | Feature state machine | Explicit events |
| Layout, theme, filters, unsubmitted drafts | Local Vue state or Pinia | Local interaction, optional persistence |

Pinia implements cross-component sharing; do not put actual machine state, interaction machines, and render objects into one global machineStore. Expose read-only snapshots/derived queries and keep writes inside controller-session. [Pinia concepts](https://pinia.vuejs.org/core-concepts/).

Avoid one universal offline/idle/running/alarm enum. Connectivity, power/emergency stop, MANUAL/MDI/AUTO, interpreter, motion, joint homing, and ownership are independent dimensions. Derived summaries may simplify display while retaining distinctions.

From day one, five-axis protocol distinguishes joints/axes, work/machine coordinates, commanded/feedback positions, millimeters/angles, and coordinate validity. Separate program read lines from motion-related lines. Verify fields against installed versions/kinematics; an XYZ tuple is not unconditionally “actual tool-tip position.”

The backend should report availability/reasons per action so UI can explain why starting is disabled. Recheck when commands arrive because state may change after display.

**6. Local state machines, not a frontend CNC controller**

Vue documents state machines for complex flows and external state integration; XState provides Vue adaptation. [Vue state machines](https://vuejs.org/guide/extras/reactivity-in-depth.html#state-machines), [XState Vue](https://stately.ai/docs/xstate-vue).

Use them for these workflows, not every dialog:

| Workflow | Example states | Value |
|---|---|---|
| Control session | Disconnected → connecting → synchronizing → operable → stale/disconnected | Socket connection alone does not enable actions |
| Command | Submitting → accepted → sent → awaiting postcondition → completed/rejected/unknown | Request issuance differs from achieved action |
| Jog gesture | Released → requesting → held/running → stopping → released/invalid | Explicit input-ending paths |
| Touch-off wizard | Enter → validate → request → observe → save/fail | Avoid uncontrolled boolean combinations |

XState tracks user progress, not predicted axis positions. Multi-step control needing deterministic behavior after UI closure belongs in the backend or validated LinuxCNC programs; frontend wizards track operation IDs.

**7. Commands and data flow**

Each connection should carry service-instance ID, machine-session ID, protocol version, and state sequence. Begin with small complete snapshots; introduce deltas only after measured bandwidth/CPU pressure, with base sequence and full-resync support.

Connection liveness and device freshness are separate. WebSocket heartbeats do not prove LinuxCNC collection is progressing. Report collection health/data age; clients use local monotonic time for receive intervals rather than subtracting unsynchronized wall clocks. Changed instances/sequence gaps trigger resynchronization.

Each action has its own request ID:

```text
User clicks Run
  → Client submits request ID, target program revision, current session
  → Server checks ownership and machine state
  → Request accepted
  → Sent to LinuxCNC
  → Observe acknowledgement and action-specific postconditions
  → Report outcome
```

HTTP success, NML processing completion, machine stopped/in-position, and whole-program completion are different. Timeout may mean unknown, never permission to assume unexecuted and resend. Deduplication applies only within defined sessions/retention. Do not promise strict exactly-once across crashes spanning physical actions.

Reconnect invalidates old operation sessions and resynchronizes. Never automatically replay home, MDI, start, resume, or jog. Restoring communication must not restore motion.

| Message | Recommended handling |
|---|---|
| Commands, acceptance, completion | WebSocket control, bounded queues, explicit IDs/results |
| Coordinates/continuous state | WebSocket state; coalesce overload to newest |
| Alarms/events | Numbered retrievable records, not overwritable like coordinates |
| Programs/preview geometry | HTTP upload/download, chunked as needed, outside control stream |
| UI layout/theme | Local state, no LinuxCNC messages |

Control/state/files are logical categories; no need for a socket per small message. Large files/geometry use separate HTTP. Separate telemetry/control connections only if measurements justify it. Application priority cannot jump ahead of data already queued on the network, so bound queues/messages at the source. [WebSocket backpressure](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API), [send buffer](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/bufferedAmount).

Generate client types from one explicit schema. FastAPI OpenAPI can generate HTTP clients; declare/validate WebSocket messages separately. HTTP OpenAPI does not automatically describe streams, and TypeScript types do not replace inbound validation. [FastAPI clients](https://fastapi.tiangolo.com/advanced/generate-clients/), [TypeScript erasure](https://www.typescriptlang.org/docs/handbook/2/classes).

**8. Continuous jogging and failures**

Jogging is a priority architecture test. Centralize pointerup, pointercancel, lost capture, focus loss, hiding, and route departure; focused inputs must not trigger global motion shortcuts. Mouse release alone misses canceled touch input. [pointercancel](https://developer.mozilla.org/en-US/docs/Web/API/Element/pointercancel_event), [page visibility](https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API).

Frontend ending events are only the first layer. Define finite operation authorization and backend timeout handling: revoke/stop renewal to end jogging. Use monotonic backend time; choose parameters from speed, braking distance, input method, and allowable response, not universal milliseconds.

Each hold gets a distinct generation, invalidated immediately on release. Late start requests/acknowledgements/renewals cannot restore it. Stop/revoke must not queue behind long work/files; revocation also rejects unsent starts from that generation. Specifically test immediate release before delayed start confirmation.

Python heartbeat cannot cover Python hanging/exiting. Configure/verify machine-side disconnect behavior and independent emergency-stop/enable chains, including physical buttons/handwheels. This is a future integration requirement, not default LinuxCNC Web-jog protection.

| Failure | Required defined behavior |
|---|---|
| Focus lost during jog | End current jog; regaining focus never resumes |
| Frozen WebView/heartbeat loss | Backend authorization expires and ends jog |
| Unresponsive service | Machine-side disconnect handling, not waiting for Web stop |
| 3D load failure | Preview unavailable; other state/workflows remain diagnosable |
| UI disconnect during automatic machining | Process-specific pause/other policy; do not reuse jog logic or promise continuation |
| Service restart | Rebind session/read-only sync; no unconfirmed-action replay |

**9. LinuxCNC session lifecycle needs its own design**

The pinned launcher runs Cleanup after foreground DISPLAY exits, stopping processes, real-time threads, and HAL. Process topology must account for this. [v2.9.4 startup/cleanup](https://github.com/LinuxCNC/linuxcnc/blob/v2.9.4/scripts/linuxcnc.in#L907).

If UI restart without rebuilding the LinuxCNC session is required, use a long-lived session host as DISPLAY, managing controlled UI startup/closure/exit requests. Python is independent of WebView but its parameters, privileges, and lifecycle bind to a specific machine session. systemd may supervise services; Restart=always alone cannot safely recover every failure.

The host coordinates lifecycle without becoming another machine-command source. Small host responsibilities may join the Python service launcher instead of another full service. Verify normal exit, UI crash, host crash, and controller exit separately in simulation. If the first release accepts ending control when UI closes, state that explicitly rather than claiming independent recovery.

**10. Five-axis preview and integrated-graphics performance**

Three.js renders; it is neither LinuxCNC interpreter nor CAM. Use an isolated preview worker with matching interpreter/machine configuration to generate geometry. Record program-content identity, coordinate/tool configuration versions, and interpretation dependencies; changes may invalidate preview.

LinuxCNC distinguishes execution and preview interpreters. Runtime probe results are unknown in preview, and custom remap must consider preview mode; arbitrary programs cannot be promised fully equivalent advance paths. [Preview/remap](https://www.linuxcnc.org/docs/2.9/html/remap/remap.html#_axis_preview_and_remapped_code_execution).

Distinguish planned program paths, sampled actual traces, and illustrative machine poses. Samples are not complete servo trajectories. Collision detection separately requires actual geometry, kinematics, and error bounds; model animation is no substitute.

Keep large immutable toolpaths in ordinary structures/shallowRef. Three.js scenes/materials/buffers remain inside the renderer, outside deeply reactive Pinia trees. Vue documents deep-reactivity overhead on huge nested data. [Vue performance](https://vuejs.org/guide/best-practices/performance.html).

Rendering recommendations:

- Batch segments/geometry rather than one object per G1.
- Keep a separate bounded live trace with cleanup.
- Consider Web Workers for decoding/geometry. Move GPU rendering to OffscreenCanvas only after checking WebKitGTK support/benefit.
- Redraw on demand while stationary; limit frame rate/pixel ratio during motion/dragging to avoid continuous GPU load.
- Provide basic 2D/disable-3D initially; graphics failures must be diagnosable/recoverable.
- Record curve discretization/model simplification accuracy; display simplification never changes executed programs.

Current WebGLRenderer requires WebGL 2. [Three.js](https://threejs.org/docs/pages/WebGLRenderer.html). Tauri documents WebKitGTK graphics failures and silent slow paths; successful context creation does not prove adequate performance. [Tauri Linux graphics](https://v2.tauri.app/develop/debug/linux-graphics/).

Intel integrated graphics is not one performance class. Record CPU/GPU generation, RAM, kernel, Mesa, WebKitGTK, X11/Wayland, resolution, and scale. Debian 13 WebKitGTK packages establish dependency availability, not acceptance of every combination. [Debian package](https://packages.debian.org/trixie/libwebkit2gtk-4.1-0).

**11. Implementing an Apple-inspired visual style**

Reka provides unstyled interaction foundations; Tailwind provides utilities/theme variables. Centralize semantic background/panel/text/separator/selection/warning/fault tokens and consume them through ui-system rather than slightly different feature-page buttons. [Reka](https://reka-ui.com/docs/overview/introduction), [Tailwind themes](https://tailwindcss.com/docs/theme).

Use stable primary action regions, restrained color, clear numbers, and whitespace. Light shadows/local transitions can express hierarchy. Heavy live blur, transparency, and continuous animation require measured GPU justification. Important state must not rely solely on color; confirmations must not wait for animation.

Ordinary buttons/inputs may reuse Reka; press-and-hold jogging needs a custom lifecycle, not click semantics. Physical-value controls need units, precision, bounds, and invalid states beyond a generic library.

Validate Tailwind v4 browser requirements on target WebKitGTK rather than equating Safari version numbers with Linux WebKitGTK. [Compatibility](https://tailwindcss.com/docs/compatibility). Bundle fonts/icons locally without offline CDN dependencies.

**12. Deployment, versions, and testing**

For fixed Debian 13 hardware, prefer .deb with explicit system dependencies and Python capable of importing distribution LinuxCNC extensions. Arbitrary Python interpreters may not load system extensions. Tauri supports Debian packaging. [Tauri Debian](https://v2.tauri.app/distribute/debian/).

Record compatible frontend/backend/protocol versions and diagnostically reject incompatible control. Upgrade through machine maintenance, designing database migration/rollback together. SQLite stores preferences, operation/alarm records, and extra metadata, not authoritative positions/modes/tool tables. Existing LinuxCNC tool tables/databases retain their owners.

| Test layer | Verify |
|---|---|
| Vitest/modules | Transitions, invalid actions, disconnect, no replay, timeout unknown, units/coordinates |
| Vue components/browser flows | Disabled reasons, keyboard/touch, drafts, navigation |
| Protocol/Python integration | Schemas, stale-session rejection, command correlation, sole error reader, restart |
| LinuxCNC simulation configuration | Homing, modes, pause, five-axis coordinates, compensation, remap, program state |
| Tauri Linux application | Actual WebKitGTK, focus, exit, fullscreen, scaling |
| Target failure/load tests | Service/window exit, graphics failure, long runs, maximum real-time jitter |

Browser tests do not fully replace Tauri. Current official guidance recommends WebdriverIO/Tauri service and native driver paths; pin compatible versions during implementation. [Tauri WebDriver](https://v2.tauri.app/develop/tests/webdriver/). Vue distinguishes unit, component, and end-to-end tests. [Vue testing](https://vuejs.org/guide/scaling-up/testing.html).

Start performance acceptance with representative real programs, then stress data. Record load time, input-response percentiles, frame time, memory growth, backend event latency, and maximum real-time jitter. Start UI sampling/refresh from a low-load baseline and adjust by measurement rather than claiming higher is better.

LinuxCNC latency guidance calls for graphics/disk load and says not to run LinuxCNC/StepConf simultaneously. Separate independent latency-plus-rendering tests from running simulation/real-machine tests. [Latency test](https://linuxcnc.org/docs/devel/html/en/install/latency-test.html).

**13. Lessons from existing open-source projects**

| Project | Evidence checked | Useful lessons | Not established |
|---|---|---|---|
| LinuxCNC AXIS / QtVCP | Official APIs/components/startup source | Preconditions, state, lifecycle, preview semantics | All interaction reusable with new CSS |
| QtPyVCP | Status plugin source | Central polling/data-channel notification | Same framework as QtVCP |
| lcncgui | README and author description | Python + WebSocket + Web frontend has precedent | Suitability for this five-axis machine/fault acceptance |
| LinuxCNC_UI | README test environments | Earlier Web-control ideas | LinuxCNC 2.7/Python 2 experience directly applies to Debian 13 |

QtPyVCP [Status source](https://www.qtpyvcp.com/_modules/qtpyvcp/plugins/status.html) shows centralized polling/notification. It is separate from QtVCP; this is architectural comparison only.

[lcncgui](https://github.com/salomom/lcncgui) describes Python/LinuxCNC/WebSocket/Web UI; its full code/hardware behavior was not audited here. [LinuxCNC_UI](https://github.com/MikhailBerezhanov/LinuxCNC_UI) lists LinuxCNC 2.7, old Debian, and Python 2 and is historical reference. Existence supports feasibility, not immediate production adoption.

**14. Implementation order and conditions for changing direction**

First, validate Tauri, Tailwind, realistically sized Three.js toolpaths, and input responsiveness on target Debian 13/Intel graphics, plus separate real-time latency load tests. Pin the hardware/system baseline after success. If WebKitGTK misses performance/stability goals, preserve Vue feature modules while comparing Chromium hosting.

Second, define protocol/session lifecycle and build read-only state, one alarm reader, and a simulation adapter. First verify that disconnect clearly invalidates UI state.

Third, implement command postconditions, mode switching, and jog-failure paths, covering UI/service/session exit in simulation. Only then integrate real actions.

Fourth, extend touch-off, tooling, program management, and five-axis preview, validating actual machine configuration item by item and unifying visuals.

Fifth, add read-only remote viewing according to actual needs. Remote control, multi-controller takeover, and runtime plugins require separate decisions, not automatic reuse of local assumptions.

Reassess microfrontends only with multiple independent teams needing independent deployment; expand state machines only as workflows grow; add data channels, binary formats, or backend processes only with benchmark evidence.

**Implementation inputs still needed:** actual LinuxCNC version/source, CPU/GPU generation, display session/specifications, axis/joint topology, controller board, primary input method, and required process behavior on UI loss during automatic machining. These do not prevent choosing module architecture but affect protocol fields, jogging, and acceptance conditions.
