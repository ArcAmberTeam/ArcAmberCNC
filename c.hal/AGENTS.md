# HAL 模块边界

遵循根目录 `AGENT.md` 和 `$code-boundary-standards`。

`c.hal/` 是 LinuxCNC HAL 的唯一源码所有者，保留核心库、组件、ClassicLadder、配置工具和用户态组件。`c` 表示主体实现语言；现有 C++ Python 绑定、混合 C/C++ 命令工具、Python 工具和 `.comp` 定义仍由所属 HAL 功能拥有，不按扩展名拆开链接单元。

公共边界沿用 `hal.h`、现有安装头文件、HAL 引脚/参数和命令行工具。`hal_priv.h` 仍是内部实现，不新增导出。上游 HAL 工具及 `src/rtapi/uspace_rtapi_app.cc` 对它的访问是保留的原生运行时内部协作例外，不可供 Qt、Rust 或 Python 控制服务跨层调用。

设备驱动实体归 `c.drivers/`；C++ 手轮驱动实体归 `cpp.drivers/`。`drivers` 和 `user_comps` 中的相对符号链接，以及根 `src/hal -> ../c.hal`，仅用于保留上游 Make、Meson、头文件导出、生成器和安装路径。它们不是第二份源码，也不定义新的公共接口。修改应访问实体目录，不得用源码副本替换链接。归档与检出必须同时保留链接及其根目录目标。

构建协调入口仍为 `src/`。目录扫描使用 `src/Makefile` 的 `HAL_SOURCE_DIRS`，因为普通 `find` 不遍历目录链接。功能内保留已有目录，仅在确有实现差异时区分平台或 CPU；不复制通用逻辑、不创建空架构目录。

验证：运行 `.github/ci/test_native_layout.py`，并在 Debian 13 容器通过 `.github/ci/native-check.sh` 运行受影响的原生模块范围。构建不得加载模块或访问设备。README 内容由人工维护。
