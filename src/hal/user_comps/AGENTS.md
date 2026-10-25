# HAL 用户态组件与设备驱动边界

遵循根目录 `AGENT.md` 和上级 `src/hal/AGENTS.md`。

本目录按完整功能拥有用户态 HAL 组件，以及 Modbus、变频器、Shuttle、XHC-HB04 和 XHC-WHB04B-6 等设备驱动及其资源。C、C++ 和 Python 实现保留在所属设备或组件目录，不因实现语言创建顶层模块。

设备驱动通过现有 HAL/RTAPI 公共接口连接控制核心。USB 报文、串口、设备状态、总线细节和 HAL 适配属于组件内部实现；保留现有 HAL 引脚、参数和命令行接口，不从应用层直接导入实现头文件。

唯一实体源码位于 `src/hal/user_comps/`，由 `src/` 中的上游 Make 统一构建。不得增加第二份源码或跨根目录兼容链接。C++ HAL 绑定和混合语言 HAL 工具继续属于各自 HAL 功能，不因扩展名搬入设备目录。

验证：运行 `.github/ci/test_native_layout.py` 和 Debian 13 中 `.github/ci/native-check.sh drivers`；修改用户态组件还须从同一原生 Make 入口构建受影响目标。XHC 手轮目标为 `../bin/xhc-hb04` 和 `../bin/xhc-whb04b-6`。构建不访问设备或加载机床控制模块，不等于真实设备行为已验证。README 内容由人工维护。
