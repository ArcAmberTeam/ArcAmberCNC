# 按业务能力划分的模块

每个一级目录拥有一项业务或基础能力。修改点动时，组件、点动展示状态、校验及测试都归 `manual-control`；接入控制器后，该模块通过会话公开接口发出意图。不得把它们拆散到全局 `components/`、`stores/`、`api/`，也不设全局 `utils/`、`common/`、`shared/` 杂物目录。

## 公开入口和私有实现

```text
manual-control/
  index.ts                 面板组件的公开入口
  presentation.ts          菜单与快捷键需要的展示接口
  lib/                     私有组件、store、校验及未来适配实现
  tests/                   模块测试和本模块夹具（需要时创建）
```

模块根文件是明确承诺维护的公开接口，所有子目录都是私有实现。允许在 `lib/` 内根据复杂度分层，但外部调用者不得知道其目录结构。模块内部实现可以互相导入；跨模块只能导入目标根文件，`import type`、动态导入、Vue SFC 同样遵循此规则。不要为了测试或省事把私有实现全部重新导出。

## 所有权和依赖

| 模块                 | 拥有的职责                                                 | 允许依赖                                                                            |
| -------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `controller-session` | 本地服务连接提示，Tauri 健康查询与结果校验；不提供机床命令 | 无其他业务模块；Tauri API 由本模块独占                                              |
| `axis-catalog`       | AXIS 入口定义、只读样例和出处                              | 无其他业务模块                                                                      |
| `ui-system`          | 无业务的控件、SVG 图标、视觉 token、Reka 组合              | 无其他业务模块                                                                      |
| `axis-presentation`  | 跨区域展示对话框宿主、入口元数据查找                       | `axis-catalog`                                                                      |
| `manual-control`     | Manual / MDI、选轴、点动选择、倍率及自身展示状态           | 上述三个基础模块                                                                    |
| `toolpath-view`      | Preview / DRO、视图选择、缩放及自身展示状态                | 上述三个基础模块                                                                    |
| `program-view`       | 程序列表、行选择、程序相关展示状态                         | 上述三个基础模块                                                                    |
| `axis-chrome`        | AXIS 菜单、工具栏与展示对话框组合                          | 上述三个基础模块；`manual-control/presentation.ts`、`toolpath-view/presentation.ts` |

`axis-presentation` 不是全局业务 store，不保存选轴、点动模式、选中程序行或预览几何。每个功能模块拥有自己的状态；只有真正跨模块的展示宿主才留在该基础模块。未来机床状态由 `controller-session` 独占会话入口，不能迁入展示 store。

`app → pages → packages`。页面可通过功能公开接口组合快捷键；功能模块不得导入其他功能模块，也不得反向导入页面、应用。`axis-chrome` 是明确的组合层，它对功能模块的依赖仅限上表指定的展示入口，不导入面板组件或 store 私有路径。所有依赖必须无环。

## 检查

规则由 [`.dependency-cruiser.cjs`](../../.dependency-cruiser.cjs) 强制执行，`npm run check` 包含 `lint:boundaries`。扫描包括 `.vue` 的脚本依赖与 TypeScript 编译前类型依赖。新增包先更新职责表和允许依赖表，不能添加忽略项绕开报错。

跨模块导入路径必须是可静态分析的字面量。Vue 的 `src` 属性、CSS `@import` 等不能用来跨模块访问私有目录；跨模块样式从公开根入口加载。这些非脚本引用仍须代码审查，不能把脚本依赖检查通过理解为覆盖了所有资源引用方式。

模块测试从公开入口验证行为，只允许使用本模块 `tests/` 中的私有夹具；生产代码不能依赖测试目录。外部浏览器测试从公开 UI 验证，不导入私有组件或 store。边界调整必须用临时非法深层导入验证检查失败，删除临时文件后再确认通过。

完整规范见 [`frontend/agent.md`](../../agent.md) 与 [根目录 `AGENT.md`](../../../AGENT.md)。

## 各模块就近说明

- [通用控件与视觉规范（`ui-system`）](ui-system/README.md)
- [功能目录与演示数据（`axis-catalog`）](axis-catalog/README.md)
- [跨区域展示对话框（`axis-presentation`）](axis-presentation/README.md)
- [桌面服务会话入口（`controller-session`）](controller-session/README.md)
- [手动操作与倍率面板（`manual-control`）](manual-control/README.md)
- [加工程序列表（`program-view`）](program-view/README.md)
- [刀路预览与坐标数显（`toolpath-view`）](toolpath-view/README.md)
- [菜单、工具栏与对话框组合（`axis-chrome`）](axis-chrome/README.md)

上层为 [应用启动](../app/README.md) 和 [页面组合](../pages/README.md)；桌面边界见 [Rust 宿主](../../src-tauri/README.md)。完整链路见 [全项目模块地图](../../../docs/module-map.md)。
