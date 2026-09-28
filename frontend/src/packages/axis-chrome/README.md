# 菜单、工具栏与对话框组合

[返回前端模块目录](../README.md) · [全项目模块地图](../../../../docs/module-map.md)

## 作用与语言

Vue、TypeScript、CSS。

组合顶部菜单、19 个工具栏入口和操作说明对话框；把显示类操作转交对应功能的公开接口。

## 入口与内部文件

`index.ts` 导出 `AxisMenubar`、`AxisToolbar`、`AxisDialogs`。

`lib/actions.ts` 处理展示动作分派；各 Vue 文件管菜单与弹窗；`lib/chrome.css` 管布局。

`lib/` 为私有实现。跨模块只能从根目录公开入口导入，不能直接引用内部文件；组件、状态和校验跟随本模块维护。

## 上下游与职责边界

允许依赖 `axis-catalog`、`axis-presentation`、`ui-system`，以及 `manual-control/presentation.ts`、`toolpath-view/presentation.ts`。

不能导入其他功能的私有组件或 store；不成为机床命令总线；运行、急停等按钮当前仅显示未接入说明。

## 修改位置与验证

增改工具栏表现改这里；手动操作规则或预览状态仍由对应模块拥有。

在 `frontend/` 运行 `npm run check` 和 `npm run build`；交互变化再运行 `npm run test:e2e` 并目视检查。不能为绕过检查而放宽模块依赖规则。
