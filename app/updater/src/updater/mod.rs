mod install;
mod release;
mod storage;
mod system;

use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use std::{io::Write, path::PathBuf};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;
const PACKAGE: &str = "betterlinuxcnc-qt";
const REPOSITORY: &str = "ArcAmberTeam/ArcAmberCNC";

#[derive(Parser)]
#[command(
    name = "betterlinuxcnc-updater",
    version,
    about = "Verified GitHub Release updates"
)]
struct Options {
    #[command(subcommand)]
    command: Action,
}

#[derive(Subcommand)]
enum Action {
    /// Check the latest stable release, download and verify the matching Debian package.
    Fetch {
        #[arg(long)]
        current_version: String,
    },
    /// Read persistent update status. No network, controller or package-manager access.
    Status,
    /// Schedule verified installation in an independent systemd user service.
    Install {
        #[arg(long)]
        socket: Option<PathBuf>,
    },
    #[command(hide = true)]
    Apply {
        #[arg(long)]
        socket: Option<PathBuf>,
    },
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Event {
    phase: String,
    message: String,
    #[serde(default)]
    version: String,
    #[serde(default)]
    progress: u8,
}

impl Event {
    fn new(phase: &str, message: impl Into<String>, version: &str, progress: u8) -> Self {
        Self {
            phase: phase.into(),
            message: message.into(),
            version: version.into(),
            progress,
        }
    }
    fn emit(&self) -> Result<()> {
        println!("{}", serde_json::to_string(self)?);
        std::io::stdout().flush()?;
        Ok(())
    }
}

pub(super) fn run() -> Result<()> {
    let options = Options::parse();
    let store = storage::Store::open()?;
    if matches!(options.command, Action::Status) {
        let status = store.status()?;
        if transient(&status) {
            if let Ok(_lock) = store.lock() {
                let latest = store.status()?;
                let installing = matches!(latest.phase.as_str(), "scheduled" | "installing");
                return if transient(&latest) && !(installing && install::is_running()?) {
                    Event::new("error", "上次更新已中断，请检查安装日志或重新下载", "", 0).emit()
                } else {
                    latest.emit()
                };
            }
        }
        return status.emit();
    }
    let result = match options.command {
        Action::Fetch { current_version } => {
            let _lock = store.lock()?;
            if matches!(store.status()?.phase.as_str(), "scheduled" | "installing") {
                install::ensure_not_scheduled()?;
            }
            release::fetch(&store, &current_version)
        }
        Action::Install { socket } => {
            let _lock = store.lock()?;
            install::schedule(&store, socket)
        }
        Action::Apply { socket } => {
            let _lock = store.wait_for_scheduler()?;
            install::apply(&store, socket)
        }
        Action::Status => unreachable!(),
    };
    if let Err(error) = &result {
        let event = Event::new("error", error.to_string(), "", 0);
        // A read-only status process can retrieve errors after the GUI restarts.
        let _ = store.publish(&event);
    }
    result
}

fn transient(event: &Event) -> bool {
    matches!(
        event.phase.as_str(),
        "checking" | "downloading" | "verifying" | "scheduled" | "installing"
    )
}
