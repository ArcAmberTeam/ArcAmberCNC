# 刀路预览与坐标数显

[返回前端模块目录](../README.md) · [全项目模块地图](../../../../docs/module-map.md)

## 作用与语言

Vue、TypeScript、Pinia、SVG、CSS。

刀路／坐标页签、显示开关、单位、视角和缩放，以及静态样例绘制。

## 入口与内部文件

`index.ts` 导出 `ToolpathView`；`presentation.ts` 导出 `useToolpathPresentation`，供菜单和快捷键操作视图。

`lib/ToolpathView.vue` 绘制静态 SVG；`lib/presentation.ts` 保存显示选择；`lib/preview.css` 管区域样式。

`lib/` 为私有实现。跨模块只能从根目录公开入口导入，不能直接引用内部文件；组件、状态和校验跟随本模块维护。

## 上下游与职责边界

允许依赖 `axis-catalog`、`axis-presentation`、`ui-system`；菜单组合层只能访问本模块的 `presentation.ts`。

当前刀路未经解释器计算，不是加工仿真。切换实际／指令位置不会产生真实反馈；不做实时插补或逆运动学。

## 修改位置与验证

将来真实预览几何与高频绘制需要独立处理；不能把大几何和控制通信塞进同一个队列。

在 `frontend/` 运行 `npm run check` 和 `npm run build`；交互变化再运行 `npm run test:e2e` 并目视检查。不能为绕过检查而放宽模块依赖规则。
