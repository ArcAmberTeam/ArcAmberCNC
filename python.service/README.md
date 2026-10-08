# Python 本地服务

[内部文件职责](src/betterlinuxcnc_service/README.md) · [全项目模块地图](../docs/module-map.md)

当前提供可运行的 Unix socket 服务，仅接受 `health` 查询。它能报告服务是否可达，始终明确返回 `machine_connected: false`；没有 LinuxCNC 导入、运动命令或 HTTP 监听。

## 开发启动

在仓库根目录执行，使用 Python 3.11 或更高版本（Debian 13 默认 Python 3.13）：

```sh
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e backend
backend/.venv/bin/python -m betterlinuxcnc_service
```

保持这个终端运行，再在另一个终端启动桌面：

```sh
cd frontend
npm ci
npm run desktop:dev
```

两者使用同一用户和相同 `XDG_RUNTIME_DIR`。默认地址是 `$XDG_RUNTIME_DIR/betterlinuxcnc/control.sock`；未设置时使用系统临时目录下的 `betterlinuxcnc/control.sock`。macOS 可用 Python 3.11+ 开发通信层，不代表 LinuxCNC 能在 macOS 运行。桌面不会自动启动或安装此服务。

`--socket /path/to/control.sock` 仅用于服务端调试和测试；桌面界面不能指定任意路径。地址所在目录须属于当前用户且权限为 `0700`，socket 权限为 `0600`。正常退出时删除本进程创建的 socket；若异常退出留下旧文件，确认没有服务进程占用后再清理。第二次启动不会覆盖已有端点。

## 协议第一版

传输为四字节大端无符号长度加 UTF-8 JSON，单帧上限 65536 字节；最多同时处理八个客户端，每次完整请求和响应限时两秒。

```json
{ "version": 1, "request_id": "example", "method": "health" }
```

```json
{
  "version": 1,
  "request_id": "example",
  "result": {
    "service": "betterlinuxcnc",
    "mode": "diagnostics-only",
    "machine_connected": false
  }
}
```

错误响应保留可识别的请求编号，以 `error.code` 表达拒绝原因。未知方法、额外字段、重复字段、非标准数字和不匹配的版本都被拒绝。服务支持一条连接内顺序查询；当前 Rust 诊断每次查询建立短连接，不构造尚未接入的控制会话或状态流。真正的持续控制会话与权限握手留待机床接入实现。

Unix socket 权限限制访问用户，不证明连接程序就是 Tauri；当前协议仅查询诊断信息，不能据此授予机床控制权。

## 检查和打包

```sh
backend/.venv/bin/python -m pip install -r backend/requirements-ci.txt
backend/.venv/bin/ruff check backend
backend/.venv/bin/ruff format --check backend
backend/.venv/bin/python -m build --no-isolation backend
backend/.venv/bin/python -m pip install --force-reinstall --no-deps backend/dist/*.whl
backend/.venv/bin/python -m unittest discover -s backend/tests -v
```

CI 在 Python 3.11 和 3.13 上构建 wheel、源码包，并测试安装后的服务。包没有第三方运行时依赖。Rust 测试还会启动真实 Python 进程验证双方消息兼容，不连接真实机床。
