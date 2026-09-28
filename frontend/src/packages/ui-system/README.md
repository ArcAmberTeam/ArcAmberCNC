# 通用控件与视觉规范

[返回前端模块目录](../README.md) · [全项目模块地图](../../../../docs/module-map.md)

## 作用与语言

Vue、TypeScript、CSS；使用 Reka UI 组合基础控件。

按钮、滑条、弹窗、SVG 图标，以及颜色、字体、焦点、悬停等统一外观。

## 入口与内部文件

`index.ts` 导出 `TkButton`、`TkRange`、`TkDialog`、`UiIcon`，并加载主题。Tk 前缀是兼容名称，已不使用 Tk 界面。

`lib/theme.css` 管颜色和基础样式；其余 Vue 文件实现控件。

`lib/` 为私有实现。跨模块只能从根目录公开入口导入，不能直接引用内部文件；组件、状态和校验跟随本模块维护。

## 上下游与职责边界

上游调用者为应用和各功能模块；不依赖任何其他业务模块。

不判断机床能否运行，不持有机床状态，不导入其他业务模块。

## 修改位置与验证

调整整站颜色改主题；改变点动按钮的业务行为应去 `manual-control`。

在 `frontend/` 运行 `npm run check` 和 `npm run build`；交互变化再运行 `npm run test:e2e` 并目视检查。不能为绕过检查而放宽模块依赖规则。
