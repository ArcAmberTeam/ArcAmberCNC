# HAL 模块边界

遵循根目录 `AGENT.md`。

`src/hal/` 是 LinuxCNC HAL 的唯一源码所有者，拥有核心库、组件、ClassicLadder、配置工具和用户态组件。现有 C++ Python 绑定、混合 C/C++ 命令工具、Python 工具和 `.comp` 定义按所属功能组织，不按实现语言拆开链接单元。

公共边界沿用 `hal.h`、现有安装头文件、HAL 引脚/参数和命令行工具。`hal_priv.h` 仍是内部实现，不新增导出。上游 HAL 工具及 `src/rtapi/uspace_rtapi_app.cc` 对它的访问是保留的原生运行时内部协作例外，不可供应用层跨层调用。

设备驱动实体位于 `drivers/`，用户态设备驱动及手轮位于 `user_comps/`，分别遵循所在目录的 `AGENTS.md`。所有目录均为真实源码路径，构建、头文件导出、生成器和归档直接使用上游目录结构，不增加跨根目录兼容链接或第二份源码。

构建协调入口为 `src/`，Make、Meson 及源码扫描均直接访问 `src/hal/`。功能内保留已有目录，仅在确有实现差异时区分平台或 CPU；不复制通用逻辑、不创建空架构目录。

验证：运行 `.github/ci/test_native_layout.py`，并在 Debian 13 容器通过 `.github/ci/native-check.sh` 运行受影响的原生模块范围。构建不得加载模块或访问设备。README 内容由人工维护。
