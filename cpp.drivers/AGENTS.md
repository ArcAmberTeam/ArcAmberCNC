# C++ 驱动模块边界

遵循根目录 `AGENT.md` 和 `$code-boundary-standards`。

`pendant/` 拥有现有 XHC-HB04、XHC-WHB04B-6 手轮驱动及其完整资源。USB 报文、设备状态和 HAL 适配是驱动内部实现；保留现有 HAL 引脚、参数和命令行接口，不从应用层直接导入实现头文件。

`c.hal/user_comps/xhc-hb04.cc` 和 `xhc-whb04b-6` 是指向本目录的相对符号链接，仅供 `src/` 中上游 Make 使用。它们不是第二份源码。C++ HAL 绑定和混合语言 HAL 工具继续属于 `c.hal/`，不能仅因扩展名搬入驱动模块。

验证：运行 `.github/ci/test_native_layout.py`，并在 Debian 13 的原生 Make 构建中验证 `../bin/xhc-hb04` 和 `../bin/xhc-whb04b-6`。构建不访问 USB 设备或加载机床控制模块。README 内容由人工维护。
