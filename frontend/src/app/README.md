# 应用启动层

[全项目模块地图](../../../docs/module-map.md) · [页面组合层](../pages/README.md)

语言为 TypeScript 和 Vue。`main.ts` 创建 Vue 应用、安装 Pinia、通过公开入口接入统一样式；`App.vue` 装配操作页面。

依赖方向是应用 → 页面 → 功能模块。这里拥有启动和应用装配，不保存点动、程序行或刀路视图的业务状态，不调用 Tauri 控制接口，不启动 Python 或 LinuxCNC。

修改应用初始化在这里；具体功能去对应 `packages` 模块。验证在 `frontend/` 执行 `npm run check` 和 `npm run build`。
