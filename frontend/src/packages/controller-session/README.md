# 桌面服务会话入口

[返回前端模块目录](../README.md) · [全项目模块地图](../../../../docs/module-map.md)

## 作用与语言

Vue、TypeScript、Tauri 前端 API。

当前只提供本地诊断组件：识别桌面环境，调用服务健康查询并校验返回结构。主页面没有挂载该组件，也不主动轮询服务。

## 入口与内部文件

`index.ts` 仅导出 `LocalServiceStatus`；没有公开运动命令 API。

`lib/client.ts` 独占 Tauri 调用；`lib/LocalServiceStatus.vue` 管诊断组件生命周期。

`lib/` 为私有实现。跨模块只能从根目录公开入口导入，不能直接引用内部文件；组件、状态和校验跟随本模块维护。

## 上下游与职责边界

不依赖其他业务模块；通过 Tauri 命令 `service_health` 进入 Rust。普通浏览器不提供控制替代通道。

服务可达不代表机床连接成功；不直接访问 Python socket、LinuxCNC 或 HAL。

## 修改位置与验证

后续会话、状态新鲜度和命令生命周期归这里；目前尚未实现。接入时同时更新允许依赖规则。

在 `frontend/` 运行 `npm run check` 和 `npm run build`；交互变化再运行 `npm run test:e2e` 并目视检查。不能为绕过检查而放宽模块依赖规则。
