# 加工程序列表

[返回前端模块目录](../README.md) · [全项目模块地图](../../../../docs/module-map.md)

## 作用与语言

Vue、TypeScript、CSS。

显示只读演示程序，维护当前选中行，提供程序相关右键入口。

## 入口与内部文件

`index.ts` 导出 `ProgramView`。

`lib/ProgramView.vue` 管展示与本地行选择；`lib/program.css` 管样式。

`lib/` 为私有实现。跨模块只能从根目录公开入口导入，不能直接引用内部文件；组件、状态和校验跟随本模块维护。

## 上下游与职责边界

允许依赖 `axis-catalog`、`axis-presentation`、`ui-system`；由页面组合。

选中行不是正在执行的程序行；不解释 G 代码，不打开真实加工文件，不发送运行命令。

## 修改位置与验证

改程序列表在这里；G 代码语义和补偿计算属于 LinuxCNC 解释器。

在 `frontend/` 运行 `npm run check` 和 `npm run build`；交互变化再运行 `npm run test:e2e` 并目视检查。不能为绕过检查而放宽模块依赖规则。
