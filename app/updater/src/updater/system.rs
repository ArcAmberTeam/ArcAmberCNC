use super::Result;
use std::{
    path::{Path, PathBuf},
    process::Command,
};

pub(super) const LAUNCHER: &str = "betterlinuxcnc-launcher.service";
pub(super) const UPDATE_UNIT: &str = "betterlinuxcnc-update.service";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) enum UnitState {
    Missing,
    Stopped,
    Running,
    Masked,
    Transition,
}

fn query(program: &Path, unit: &str) -> Result<UnitState> {
    let output = Command::new(program)
        .args([
            "--user",
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

pub(super) fn state(unit: &str) -> Result<UnitState> {
    query(Path::new("/usr/bin/systemctl"), unit)
}

fn control(program: &Path, arguments: &[&str]) -> Result<()> {
    let output = Command::new(program)
        .arg("--user")
        .args(arguments)
        .output()?;
    if !output.status.success() {
        return Err("无法正常暂停或恢复启动器，请检查 systemd 用户日志".into());
    }
    Ok(())
}

pub(super) struct PausedLauncher {
    program: PathBuf,
    masked: bool,
    restart: bool,
}

impl PausedLauncher {
    pub fn stop(original: UnitState) -> Result<Self> {
        Self::stop_with(Path::new("/usr/bin/systemctl"), original)
    }
    fn stop_with(program: &Path, original: UnitState) -> Result<Self> {
        if original == UnitState::Transition {
            return Err("启动器正在切换状态，请稍后重试".into());
        }
        let mut guard = Self {
            program: program.to_owned(),
            masked: false,
            restart: original == UnitState::Running,
        };
        if original != UnitState::Missing {
            if original != UnitState::Masked {
                control(program, &["mask", "--runtime", LAUNCHER])?;
                guard.masked = true;
            }
            // Stop even an inactive/failed unit: cancel any queued automatic restart.
            control(program, &["stop", LAUNCHER])?;
            let state = query(program, LAUNCHER)?;
            if !matches!(state, UnitState::Masked | UnitState::Stopped) {
                return Err("启动器未正常停止，未安装更新".into());
            }
        }
        Ok(guard)
    }
    fn unmask(&mut self) -> Result<()> {
        if self.masked {
            control(&self.program, &["unmask", "--runtime", LAUNCHER])?;
            self.masked = false;
        }
        Ok(())
    }
    pub fn resume(mut self) -> Result<()> {
        self.unmask()?;
        if self.restart {
            control(&self.program, &["start", LAUNCHER])?;
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
    use std::{fs, os::unix::fs::PermissionsExt};
    fn executable(directory: &Path, script: &str) -> PathBuf {
        let path = directory.join("systemctl");
        fs::write(&path, format!("#!/bin/sh\n{script}\n")).unwrap();
        fs::set_permissions(&path, fs::Permissions::from_mode(0o700)).unwrap();
        path
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
            assert_eq!(query(&path, LAUNCHER).unwrap(), expected);
        }
        let path = executable(
            directory.path(),
            "echo 'Failed to connect to bus' >&2; exit 1",
        );
        assert!(query(&path, LAUNCHER).is_err());
        let path = executable(
            directory.path(),
            "printf 'LoadState=loaded\\nActiveState=unknown\\n'",
        );
        assert!(query(&path, LAUNCHER).is_err());
    }
    #[test]
    fn pause_masks_before_stop_and_restores_only_an_originally_running_launcher() {
        let directory = tempfile::tempdir().unwrap();
        let log = directory.path().join("calls");
        let script = format!("echo \"$*\" >> '{}'\nif [ \"$2\" = show ]; then printf 'LoadState=masked\\nActiveState=inactive\\n'; fi", log.display());
        let program = executable(directory.path(), &script);
        PausedLauncher::stop_with(&program, UnitState::Running)
            .unwrap()
            .resume()
            .unwrap();
        let calls = fs::read_to_string(&log).unwrap();
        let lines: Vec<_> = calls.lines().collect();
        assert_eq!(lines[0], format!("--user mask --runtime {LAUNCHER}"));
        assert_eq!(lines[1], format!("--user stop {LAUNCHER}"));
        assert_eq!(lines[3], format!("--user unmask --runtime {LAUNCHER}"));
        assert_eq!(lines[4], format!("--user start {LAUNCHER}"));
        fs::write(&log, "").unwrap();
        drop(PausedLauncher::stop_with(&program, UnitState::Stopped).unwrap());
        let calls = fs::read_to_string(&log).unwrap();
        assert!(calls.contains("stop"));
        assert!(calls.contains("unmask"));
        assert!(!calls.contains("start"));
    }
}
