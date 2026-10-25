use super::Result;
use std::path::PathBuf;

pub(super) const LAUNCHER: &str = "betterlinuxcnc-launcher.service";
pub(super) const UPDATE_UNIT: &str = "betterlinuxcnc-system-update.service";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) enum UnitState {
    Missing,
    Stopped,
    Running,
    Masked,
    Transition,
}

#[derive(Clone)]
pub(super) struct Manager {
    program: PathBuf,
    account: Option<(String, u32)>,
    system: bool,
}

impl Manager {
    pub fn system() -> Self {
        Self {
            program: "/usr/bin/systemctl".into(),
            account: None,
            system: true,
        }
    }
    pub fn account(name: &str, uid: u32) -> Self {
        Self {
            program: "/usr/bin/systemctl".into(),
            account: Some((name.into(), uid)),
            system: false,
        }
    }
    fn command(&self) -> std::process::Command {
        let mut command = if let Some((name, uid)) = &self.account {
            let mut command = super::command("/usr/sbin/runuser");
            command
                .args([
                    "-u",
                    name,
                    "--",
                    "/usr/bin/env",
                    "-i",
                    "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                ])
                .arg(format!("XDG_RUNTIME_DIR=/run/user/{uid}"))
                .arg(format!(
                    "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus"
                ))
                .arg("HOME=/var/lib/betterlinuxcnc/home")
                .arg(&self.program);
            command
        } else {
            super::command(&self.program)
        };
        command.arg(if self.system { "--system" } else { "--user" });
        if self.system {
            command.arg("--no-ask-password");
        }
        command
    }
    pub fn state(&self, unit: &str) -> Result<UnitState> {
        query(self, unit)
    }
    pub fn control(&self, arguments: &[&str]) -> Result<()> {
        let output = self.command().args(arguments).output()?;
        if !output.status.success() {
            return Err("无法正常暂停或恢复启动器，请检查 systemd 日志".into());
        }
        Ok(())
    }
}

fn query(manager: &Manager, unit: &str) -> Result<UnitState> {
    let output = manager
        .command()
        .args([
            "show",
            unit,
            "--property=LoadState",
            "--property=ActiveState",
        ])
        .output()?;
    let text = String::from_utf8(output.stdout)?;
    let fields: std::collections::HashMap<_, _> = text
        .lines()
        .filter_map(|line| line.split_once('='))
        .collect();
    let load = fields
        .get("LoadState")
        .copied()
        .ok_or("systemd 未返回加载状态")?;
    let active = fields
        .get("ActiveState")
        .copied()
        .ok_or("systemd 未返回运行状态")?;
    if !output.status.success() {
        if load == "not-found" && active == "inactive" {
            return Ok(UnitState::Missing);
        }
        return Err("无法查询 systemd 用户服务，未执行安装".into());
    }
    if matches!(
        active,
        "activating" | "deactivating" | "reloading" | "refreshing" | "maintenance"
    ) {
        return Ok(UnitState::Transition);
    }
    match (load, active) {
        ("loaded", "active") => Ok(UnitState::Running),
        ("loaded", "inactive" | "failed") => Ok(UnitState::Stopped),
        ("masked", "inactive" | "failed") => Ok(UnitState::Masked),
        ("not-found", "inactive") => Ok(UnitState::Missing),
        _ => Err(format!("systemd 服务状态未知：{load}/{active}").into()),
    }
}

pub(super) struct PausedLauncher {
    manager: Manager,
    masked: bool,
    restart: bool,
}

impl PausedLauncher {
    pub fn stop(manager: Manager, original: UnitState) -> Result<Self> {
        if original == UnitState::Transition {
            return Err("启动器正在切换状态，请稍后重试".into());
        }
        let mut guard = Self {
            manager,
            masked: false,
            restart: original == UnitState::Running,
        };
        if original != UnitState::Missing {
            if original != UnitState::Masked {
                guard.manager.control(&["mask", "--runtime", LAUNCHER])?;
                guard.masked = true;
            }
            // Stop even an inactive/failed unit: cancel any queued automatic restart.
            guard.manager.control(&["stop", LAUNCHER])?;
            let state = guard.manager.state(LAUNCHER)?;
            if !matches!(state, UnitState::Masked | UnitState::Stopped) {
                return Err("启动器未正常停止，未安装更新".into());
            }
        }
        Ok(guard)
    }
    fn unmask(&mut self) -> Result<()> {
        if self.masked {
            self.manager.control(&["unmask", "--runtime", LAUNCHER])?;
            self.masked = false;
        }
        Ok(())
    }
    pub fn resume(mut self) -> Result<()> {
        // The package may have replaced the user unit while it was masked.
        self.manager.control(&["daemon-reload"])?;
        self.unmask()?;
        if self.restart {
            self.manager.control(&["start", LAUNCHER])?;
        }
        Ok(())
    }
}

impl Drop for PausedLauncher {
    fn drop(&mut self) {
        // Failed installation remains stopped. Do not leave a mask we introduced.
        let _ = self.unmask();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{fs, os::unix::fs::PermissionsExt, path::Path};
    fn manager(program: &Path) -> Manager {
        Manager {
            program: program.to_owned(),
            account: None,
            system: false,
        }
    }
    fn executable(directory: &Path, script: &str) -> PathBuf {
        let path = directory.join("systemctl");
        fs::write(&path, format!("#!/bin/sh\n{script}\n")).unwrap();
        fs::set_permissions(&path, fs::Permissions::from_mode(0o700)).unwrap();
        path
    }
    #[test]
    fn privileged_user_manager_uses_fixed_drop_and_clean_environment() {
        let manager = Manager::account("linuxcnc", 1001);
        let process = manager.command();
        assert_eq!(process.get_program(), "/usr/sbin/runuser");
        let args: Vec<_> = process
            .get_args()
            .map(|arg| arg.to_str().unwrap())
            .collect();
        assert_eq!(
            args,
            [
                "-u",
                "linuxcnc",
                "--",
                "/usr/bin/env",
                "-i",
                "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                "XDG_RUNTIME_DIR=/run/user/1001",
                "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus",
                "HOME=/var/lib/betterlinuxcnc/home",
                "/usr/bin/systemctl",
                "--user"
            ]
        );
        assert!(process
            .get_envs()
            .all(|(key, _)| key == "PATH" || key == "LANG"));
        let system = Manager::system().command();
        assert_eq!(system.get_program(), "/usr/bin/systemctl");
        assert_eq!(
            system.get_args().collect::<Vec<_>>(),
            ["--system", "--no-ask-password"]
        );
    }

    #[test]
    fn actual_process_exit_status_and_transition_states_are_not_assumed_inactive() {
        let directory = tempfile::tempdir().unwrap();
        for (load, active, expected) in [
            ("loaded", "active", UnitState::Running),
            ("loaded", "inactive", UnitState::Stopped),
            ("loaded", "failed", UnitState::Stopped),
            ("loaded", "activating", UnitState::Transition),
            ("loaded", "deactivating", UnitState::Transition),
            ("masked", "inactive", UnitState::Masked),
            ("not-found", "inactive", UnitState::Missing),
        ] {
            let path = executable(
                directory.path(),
                &format!("printf 'LoadState={load}\\nActiveState={active}\\n'"),
            );
            assert_eq!(query(&manager(&path), LAUNCHER).unwrap(), expected);
        }
        let path = executable(
            directory.path(),
            "echo 'Failed to connect to bus' >&2; exit 1",
        );
        assert!(query(&manager(&path), LAUNCHER).is_err());
        let path = executable(
            directory.path(),
            "printf 'LoadState=loaded\\nActiveState=unknown\\n'",
        );
        assert!(query(&manager(&path), LAUNCHER).is_err());
    }
    #[test]
    fn pause_masks_before_stop_and_restores_only_an_originally_running_launcher() {
        let directory = tempfile::tempdir().unwrap();
        let log = directory.path().join("calls");
        let script = format!("echo \"$*\" >> '{}'\nif [ \"$2\" = show ]; then printf 'LoadState=masked\\nActiveState=inactive\\n'; fi", log.display());
        let program = executable(directory.path(), &script);
        PausedLauncher::stop(manager(&program), UnitState::Running)
            .unwrap()
            .resume()
            .unwrap();
        let calls = fs::read_to_string(&log).unwrap();
        let lines: Vec<_> = calls.lines().collect();
        assert_eq!(lines[0], format!("--user mask --runtime {LAUNCHER}"));
        assert_eq!(lines[1], format!("--user stop {LAUNCHER}"));
        assert_eq!(lines[3], "--user daemon-reload");
        assert_eq!(lines[4], format!("--user unmask --runtime {LAUNCHER}"));
        assert_eq!(lines[5], format!("--user start {LAUNCHER}"));
        fs::write(&log, "").unwrap();
        drop(PausedLauncher::stop(manager(&program), UnitState::Stopped).unwrap());
        let calls = fs::read_to_string(&log).unwrap();
        assert!(calls.contains("stop"));
        assert!(calls.contains("unmask"));
        assert!(!calls.contains("start"));
        assert!(!calls.contains("daemon-reload"));
        fs::write(&log, "").unwrap();
        PausedLauncher::stop(manager(&program), UnitState::Stopped)
            .unwrap()
            .resume()
            .unwrap();
        let calls = fs::read_to_string(&log).unwrap();
        assert!(calls.contains("--user daemon-reload"));
        assert!(!calls.contains("start"));
    }

    #[test]
    fn failed_user_daemon_reload_does_not_restart_the_launcher() {
        let directory = tempfile::tempdir().unwrap();
        let log = directory.path().join("calls");
        let script = format!("echo \"$*\" >> '{}'\nif [ \"$2\" = daemon-reload ]; then exit 1; fi\nif [ \"$2\" = show ]; then printf 'LoadState=masked\\nActiveState=inactive\\n'; fi", log.display());
        let program = executable(directory.path(), &script);
        assert!(PausedLauncher::stop(manager(&program), UnitState::Running)
            .unwrap()
            .resume()
            .is_err());
        let calls = fs::read_to_string(&log).unwrap();
        assert!(calls.contains("--user daemon-reload"));
        assert!(calls.contains("unmask"));
        assert!(!calls.contains("start"));
    }
}
