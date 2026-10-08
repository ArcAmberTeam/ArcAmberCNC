# C 驱动模块边界

遵循根目录 `AGENT.md` 和 `$code-boundary-standards`。

本目录拥有原 `src/hal/drivers/` 的设备驱动及其生成器、固件资源、说明文件；`user/` 拥有已迁移的 Modbus、变频器和 Shuttle C 用户态驱动。按完整设备能力保留现有源码和资源，不能仅按扩展名拆分。

驱动通过现有 HAL/RTAPI 公共接口连接控制核心；设备寄存器、USB、串口、总线及固件细节属于驱动私有实现。平台通用逻辑不复制到多个 CPU 目录；已有 Mesa、Raspberry Pi、BeagleBone 和通用 GPIO 实现保持原有边界。CPU 架构、设备平台、实时运行环境不能混为一层。

`c.hal/drivers -> ../c.drivers` 和 `c.hal/user_comps/` 中指向 `user/` 的相对链接是上游构建兼容入口，唯一实体源码在本目录。构建仍从 `src/` 运行；不要直接在本目录执行独立构建或创建第二份源码。保留生成文件与安装接口，不把私有头文件导出给应用层。

验证：运行 `.github/ci/test_native_layout.py` 和 Debian 13 中 `.github/ci/native-check.sh drivers`。修改用户态驱动还须从同一原生 Make 入口构建受影响的用户态目标。不得因构建成功声称设备或实时行为已验证。README 内容由人工维护。
