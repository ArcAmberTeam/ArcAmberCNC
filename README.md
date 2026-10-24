配置文件位置：`./launcher.json`，用于配置机床与启动编排。模板：`./launcher.example.json`。相对路径均以配置文件所在目录为准。

- `ini`：机床 INI 路径，`[DISPLAY] DISPLAY` 设为 `betterlinuxcnc`。
- `startup_timeout`、`shutdown_timeout`：启动等待、退出等待秒数。
- `cam.host`、`cam.port`：机床 TCP 监听地址与端口，默认端口 6522。
- `cam.inbox`：G-code 收件目录。
- `cam.token_file`：配对令牌文件，权限 0600。
- `cam.cert`、`cam.key`：TLS 证书与私钥文件。
- `cam.auto_run`：是否收到新 G-code 后提交加工，默认 false。
- `cam.discovery.device_id`、`device_name`、`address`：稳定设备 UUID、名称、广播地址；UDP 端口 8421。
- `cam` 设为 null：不启用 CAM 联动。

启动方式：安装后，在项目目录运行 `betterlinuxcnc-launch`；检查配置运行 `betterlinuxcnc-launch --check`；指定项目配置运行 `betterlinuxcnc-launch --config /项目路径/launcher.json`。

安装默认自动启动项目：`/opt/arcambercnc/launcher.json`。编译时用 `-DBETTERCNC_PROJECT_DIR=/项目路径` 指定。进入桌面会话后自动启动并保活；无人操作开机需系统开启用户自动登录。

手动停止：`systemctl --user stop betterlinuxcnc-launcher.service`，或 kill 主启动器进程；本次会话不再自动拉起。单次运行不保活：`betterlinuxcnc-launch --once`。
