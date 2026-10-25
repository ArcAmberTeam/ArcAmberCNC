use super::{
    storage::{self, Store},
    Event, Result,
};
use serde_json::{json, Value};
use std::{
    fs,
    io::{Read, Write},
    os::unix::{
        fs::{FileTypeExt, MetadataExt},
        net::UnixStream,
    },
    path::{Path, PathBuf},
    process::Command,
    time::Duration,
};

use super::system::{self, PausedLauncher, UnitState, LAUNCHER, UPDATE_UNIT};

pub(super) fn architecture() -> Result<String> {
    let output = Command::new("/usr/bin/dpkg")
        .arg("--print-architecture")
        .output()?;
    let value = String::from_utf8(output.stdout)?.trim().to_owned();
    if !output.status.success() || !matches!(value.as_str(), "amd64" | "arm64" | "i386" | "armhf") {
        return Err("当前 Debian 架构不受支持".into());
    }
    Ok(value)
}

fn socket_path(path: Option<PathBuf>) -> PathBuf {
    path.unwrap_or_else(|| {
        std::env::var_os("XDG_RUNTIME_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(std::env::temp_dir)
            .join("betterlinuxcnc/control.sock")
    })
}

pub(super) fn ensure_not_scheduled() -> Result<()> {
    if is_running()? {
        return Err("安装更新任务正在运行，请等待完成".into());
    }
    Ok(())
}

pub(super) fn is_running() -> Result<bool> {
    if !cfg!(target_os = "linux") {
        return Ok(false);
    }
    Ok(!matches!(
        system::state(UPDATE_UNIT)?,
        UnitState::Stopped | UnitState::Missing | UnitState::Masked
    ))
}

fn observed(path: &Path) -> Result<Value> {
    let parent = fs::symlink_metadata(path.parent().ok_or("控制端点目录无效")?)?;
    let info = fs::symlink_metadata(path)?;
    let uid = unsafe { libc::getuid() };
    if !parent.is_dir()
        || parent.uid() != uid
        || parent.mode() & 0o077 != 0
        || !info.file_type().is_socket()
        || info.uid() != uid
        || info.mode() & 0o077 != 0
    {
        return Err("控制服务端点不是当前用户的私有 socket".into());
    }
    let mut stream = UnixStream::connect(path)?;
    stream.set_read_timeout(Some(Duration::from_secs(2)))?;
    stream.set_write_timeout(Some(Duration::from_secs(2)))?;
    let id = uuid::Uuid::new_v4().to_string();
    let request = serde_json::to_vec(
        &json!({"version":2,"request_id":id,"method":"machine.status","params":{}}),
    )?;
    stream.write_all(&(request.len() as u32).to_be_bytes())?;
    stream.write_all(&request)?;
    let mut length = [0; 4];
    stream.read_exact(&mut length)?;
    let size = u32::from_be_bytes(length) as usize;
    if size == 0 || size > 65536 {
        return Err("控制器状态报文长度无效".into());
    }
    let mut body = vec![0; size];
    stream.read_exact(&mut body)?;
    let response: Value = serde_json::from_slice(&body)?;
    if response["version"] != 2
        || response["request_id"] != id
        || response.get("error").is_some()
        || !response["result"].is_object()
    {
        return Err("控制器状态身份或格式无效".into());
    }
    Ok(response["result"].clone())
}

fn quiescent(state: &Value) -> bool {
    state["connected"] == true
        && state["powered"] == false
        && state["busy"] == false
        && matches!(
            state["programState"].as_str(),
            Some("idle" | "off" | "estop")
        )
        && state["queueDepth"].as_u64() == Some(0)
        && state["activeQueueDepth"].as_u64() == Some(0)
        && state["paused"] == false
        && state["velocity"]
            .as_f64()
            .is_some_and(|v| v.abs() < 0.00001)
        && state["spindleSpeed"]
            .as_f64()
            .is_some_and(|v| v.abs() < 0.01)
        && matches!(state["nativeCommandState"].as_str(), Some("done" | "error"))
        && !matches!(
            state["commandState"].as_str(),
            Some("accepted" | "pending" | "sent" | "unknown")
        )
        && ["job", "camJob"].iter().all(|field| {
            !matches!(
                state[field]["state"].as_str(),
                Some("accepted" | "loading" | "starting" | "running" | "unknown")
            )
        })
}

fn preflight(path: &Path) -> Result<UnitState> {
    let state = system::state(LAUNCHER)?;
    if state == UnitState::Transition {
        return Err("启动器正在切换状态，请稍后重试".into());
    }
    if state == UnitState::Running {
        if !quiescent(&observed(path)?) {
            return Err("请先停止加工和主轴、关闭机床使能，确认空闲后再安装更新".into());
        }
    } else if path.try_exists()? || Path::new("/tmp/linuxcnc.lock").try_exists()? {
        return Err("存在未由启动器管理的机床进程，请先正常退出控制系统".into());
    }
    Ok(state)
}

pub(super) fn schedule(store: &Store, socket: Option<PathBuf>) -> Result<()> {
    if !cfg!(target_os = "linux") {
        return Err("安装更新仅支持 Debian".into());
    }
    ensure_not_scheduled()?;
    let staged = store.staged()?;
    let path = socket_path(socket);
    preflight(&path)?;
    let mut command = Command::new("/usr/bin/systemd-run");
    command.args([
        "--user",
        "--collect",
        "--quiet",
        "--unit",
        UPDATE_UNIT,
        "--property=Type=exec",
    ]);
    for variable in ["DISPLAY", "XAUTHORITY", "WAYLAND_DISPLAY", "XDG_CACHE_HOME"] {
        if let Some(value) = std::env::var_os(variable) {
            let mut argument = std::ffi::OsString::from(format!("--setenv={variable}="));
            argument.push(value);
            command.arg(argument);
        }
    }
    command
        .arg(std::env::current_exe()?)
        .arg("apply")
        .arg("--socket")
        .arg(&path);
    // Persist before dispatch: the independent worker may immediately stop the GUI.
    let pending = Event::new(
        "scheduled",
        "安装任务已提交；控制界面将关闭，完成后重新启动",
        &staged.version,
        100,
    );
    store.save("status.json", &pending)?;
    let output = command.output()?;
    if !output.status.success() {
        return Err("无法启动独立更新服务，请检查 systemd 用户会话".into());
    }
    pending.emit()
}

pub(super) fn apply(store: &Store, socket: Option<PathBuf>) -> Result<()> {
    let staged = store.staged()?;
    if staged.architecture != architecture()? {
        return Err("安装包架构与本机不符".into());
    }
    let package = store.directory.join("package.deb");
    let (version, arch) = storage::package_info(&package)?;
    if version != staged.version || arch != staged.architecture {
        return Err("安装包信息已改变，请重新下载".into());
    }
    let installed = storage::installed_version("0")?;
    if !storage::newer(&version, &installed)? {
        return Err("拒绝安装相同或更低版本".into());
    }
    let path = socket_path(socket);
    let original = preflight(&path)?;
    store.publish(&Event::new(
        "installing",
        "正在准备安装更新…",
        &version,
        100,
    ))?;
    let launcher = PausedLauncher::stop(original)?;
    // The launcher's own shutdown guard is authoritative; retained processes veto installation.
    if path.try_exists()? || Path::new("/tmp/linuxcnc.lock").try_exists()? {
        return Err("控制系统仍在运行，未安装更新，请检查启动器日志".into());
    }
    store.staged()?;
    let output = Command::new("/usr/bin/pkexec")
        .arg("/usr/bin/apt-get")
        .args(["--yes", "--no-remove", "install"])
        .arg(&package)
        .output()?;
    let mut log = output.stdout;
    log.extend_from_slice(&output.stderr);
    fs::write(store.directory.join("install.log"), &log)?;
    if !output.status.success() {
        if matches!(output.status.code(), Some(126 | 127)) {
            let _ = launcher.resume();
            return Err("安装授权被取消或不可用；更新未完成".into());
        }
        return Err("安装失败；未自动重启控制系统，请查看更新缓存中的 install.log".into());
    }
    if storage::installed_version("0")? != version {
        return Err("安装器结束但版本核验不符，未报告更新成功".into());
    }
    launcher
        .resume()
        .map_err(|error| format!("更新已安装，但控制系统恢复失败：{error}"))?;
    store.publish(&Event::new(
        "complete",
        format!("已更新至 {version}"),
        &version,
        100,
    ))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn real_status_reader_and_service_observer_contract() {
        use std::{
            env,
            os::unix::fs::PermissionsExt,
            process::{Child, Stdio},
            thread,
            time::Instant,
        };
        struct Host(Child);
        impl Drop for Host {
            fn drop(&mut self) {
                unsafe {
                    libc::kill(self.0.id() as i32, libc::SIGTERM);
                }
                let deadline = Instant::now() + Duration::from_secs(3);
                while Instant::now() < deadline {
                    if self.0.try_wait().ok().flatten().is_some() {
                        return;
                    }
                    thread::sleep(Duration::from_millis(10));
                }
                let _ = self.0.kill();
                let _ = self.0.wait();
            }
        }
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .to_owned();
        let python = env::var_os("SERVICE_TEST_PYTHON").unwrap_or_else(|| "python3".into());
        let paths = env::join_paths([
            root.join("app/controller/src"),
            root.join("app/controller/tests"),
        ])
        .unwrap();
        for scenario in [
            "off",
            "busy",
            "native-pending",
            "unknown-velocity",
            "powered",
        ] {
            let directory = tempfile::tempdir_in("/tmp").unwrap();
            fs::set_permissions(directory.path(), fs::Permissions::from_mode(0o700)).unwrap();
            let path = directory.path().join("control.sock");
            let child = Command::new(&python)
                .arg(root.join("app/updater/tests/observer_host.py"))
                .arg(&path)
                .arg(scenario)
                .env("PYTHONPATH", &paths)
                .stdout(Stdio::null())
                .spawn()
                .unwrap();
            let _host = Host(child);
            let deadline = Instant::now() + Duration::from_secs(5);
            let status = loop {
                if path.exists() {
                    if let Ok(status) = observed(&path) {
                        break status;
                    }
                }
                assert!(
                    Instant::now() < deadline,
                    "observer did not become ready: {scenario}"
                );
                thread::sleep(Duration::from_millis(10));
            };
            assert_eq!(
                quiescent(&status),
                scenario == "off",
                "{scenario}: {status}"
            );
        }
    }
    #[test]
    fn observes_only_public_status_and_rejects_mismatched_reply() {
        use std::{
            os::unix::{fs::PermissionsExt, net::UnixListener},
            thread,
        };
        for correct_id in [true, false] {
            let directory = tempfile::tempdir().unwrap();
            fs::set_permissions(directory.path(), fs::Permissions::from_mode(0o700)).unwrap();
            let path = directory.path().join("control.sock");
            let server = UnixListener::bind(&path).unwrap();
            fs::set_permissions(&path, fs::Permissions::from_mode(0o600)).unwrap();
            let worker = thread::spawn(move || {
                let (mut stream, _) = server.accept().unwrap();
                let mut size = [0; 4];
                stream.read_exact(&mut size).unwrap();
                let mut body = vec![0; u32::from_be_bytes(size) as usize];
                stream.read_exact(&mut body).unwrap();
                let request: Value = serde_json::from_slice(&body).unwrap();
                assert_eq!(request["method"], "machine.status");
                assert_eq!(request["params"], json!({}));
                let response = serde_json::to_vec(&json!({"version":2,
                    "request_id":if correct_id {request["request_id"].clone()} else {json!("other")},
                    "result":{"connected":true}})).unwrap();
                stream
                    .write_all(&(response.len() as u32).to_be_bytes())
                    .unwrap();
                stream.write_all(&response).unwrap();
            });
            assert_eq!(observed(&path).is_ok(), correct_id);
            worker.join().unwrap();
        }
    }
    #[test]
    fn unknown_paused_queued_or_powered_machines_cannot_install() {
        let safe = json!({"connected":true,"powered":false,"busy":false,"paused":false,
            "programState":"idle","queueDepth":0,"activeQueueDepth":0,"velocity":0,
            "spindleSpeed":0,"nativeCommandState":"done"});
        assert!(quiescent(&safe));
        for (field, value) in [
            ("connected", json!(false)),
            ("powered", json!(true)),
            ("paused", json!(true)),
            ("busy", json!(true)),
            ("queueDepth", json!(1)),
            ("activeQueueDepth", json!(1)),
            ("spindleSpeed", json!(100)),
            ("velocity", json!(1)),
            ("commandState", json!("unknown")),
            ("nativeCommandState", json!("executing")),
        ] {
            let mut state = safe.clone();
            state[field] = value;
            assert!(!quiescent(&state), "{field}");
        }
        for field in [
            "programState",
            "queueDepth",
            "velocity",
            "spindleSpeed",
            "nativeCommandState",
        ] {
            let mut state = safe.clone();
            state.as_object_mut().unwrap().remove(field);
            assert!(!quiescent(&state), "missing {field}");
        }
        let mut state = safe;
        state["job"] = json!({"state":"running"});
        assert!(!quiescent(&state));
    }
}
