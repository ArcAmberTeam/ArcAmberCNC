# HAL 设备驱动边界

遵循根目录 `AGENT.md` 和上级 `src/hal/AGENTS.md`。

本目录拥有 HAL 设备驱动及其生成器、固件资源和说明文件。按完整设备能力保留源码和资源，不能仅按实现语言或扩展名拆分。Modbus、变频器、Shuttle 和 XHC 手轮等用户态设备能力位于同级 `user_comps/`。

驱动通过现有 HAL/RTAPI 公共接口连接控制核心；设备寄存器、USB、串口、总线及固件细节属于驱动私有实现。平台通用逻辑不复制到多个 CPU 目录；已有 Mesa、Raspberry Pi、BeagleBone 和通用 GPIO 实现保持原有边界。CPU 架构、设备平台、实时运行环境不能混为一层。

唯一实体源码位于 `src/hal/drivers/`，构建从 `src/` 运行；不要直接在本目录执行独立构建或创建第二份源码。保留生成文件与安装接口，不把私有头文件导出给应用层。

验证：运行 `.github/ci/test_native_layout.py` 和 Debian 13 中 `.github/ci/native-check.sh drivers`。不得因构建成功声称设备或实时行为已验证。README 内容由人工维护。
