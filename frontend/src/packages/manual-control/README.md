# 手动操作与倍率面板

[返回前端模块目录](../README.md) · [全项目模块地图](../../../../docs/module-map.md)

## 作用与语言

Vue、TypeScript、Pinia、CSS。

手动操作／手动输入切换、选轴、点动方式、回零与对刀入口、主轴和冷却入口、倍率显示。

## 入口与内部文件

`index.ts` 导出 `ManualControl`；`presentation.ts` 导出菜单和页面需要的 `useManualPresentation`。

`lib/ManualControl.vue` 管面板和局部输入；`lib/presentation.ts` 管跨区域所需的手动展示状态；`lib/manual.css` 管布局。

`lib/` 为私有实现。跨模块只能从根目录公开入口导入，不能直接引用内部文件；组件、状态和校验跟随本模块维护。

## 上下游与职责边界

允许依赖 `axis-catalog`、`axis-presentation`、`ui-system`；菜单组合层只能访问本模块的 `presentation.ts`。

机床按钮只打开未接入说明；滑条值不是设备反馈。不能直接调用 Tauri，也不能读取其他功能模块的私有状态。

## 修改位置与验证

修改点动面板在这里；未来实际操作校验归 Python，回零运动算法归 LinuxCNC。

在 `frontend/` 运行 `npm run check` 和 `npm run build`；交互变化再运行 `npm run test:e2e` 并目视检查。不能为绕过检查而放宽模块依赖规则。
