# 页面组合层

[全项目模块地图](../../../docs/module-map.md) · [功能模块目录](../packages/README.md)

语言为 Vue、TypeScript 和 CSS。`AxisPage.vue` 将菜单、工具栏、手动面板、刀路区域与程序列表组合为操作台，拥有页面尺寸、分隔条及跨区域快捷键。

页面只从功能模块的公开入口取组件和展示接口；功能模块不能反向依赖页面。页面不持有设备连接或运动规则，不直接调用 Tauri、Python 或 HAL。

当前不挂载 `LocalServiceStatus`，不发起健康轮询；不显示品牌图标或底部状态栏。程序区缩放属于页面布局，刀路缩放属于 `toolpath-view`。

修改布局运行 `npm run check`、`npm run build`；影响分隔条、快捷键等交互时再运行 `npm run test:e2e`，并检查最小窗口显示。
