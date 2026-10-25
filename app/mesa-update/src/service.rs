use crate::contract::Manifest;
use crate::platform;
use crate::release::{self, Fetch, OfficialHttp};
use crate::storage::Store;
use crate::Result;
use serde::{Deserialize, Serialize};
use std::io::Write;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Status {
    schema_version: u32,
    component: String,
    phase: String,
    message: String,
    updated_unix: u64,
    installed_app_version: Option<String>,
    available_version: Option<String>,
    app_latest_version: Option<String>,
    mesa_latest_version: Option<String>,
    manifest: Option<Manifest>,
    firmware_downloaded: bool,
    flash_enabled: bool,
}

impl Status {
    fn new(component: &str, phase: &str, message: &str) -> Self {
        Self {
            schema_version: 1,
            component: component.into(),
            phase: phase.into(),
            message: message.into(),
            updated_unix: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
            installed_app_version: None,
            available_version: None,
            app_latest_version: None,
            mesa_latest_version: None,
            manifest: None,
            firmware_downloaded: false,
            // No release or local cache is allowed to enable hardware writes.
            flash_enabled: false,
        }
    }
}

pub(crate) fn update_status() -> Result<()> {
    let uid = platform::require_operator()?;
    show_status(Store::user(uid, false)?, "mesa-update")
}

pub(crate) fn flash_status() -> Result<()> {
    show_status(Store::root_state(false)?, "mesa-flash")
}

fn show_status(store: Option<Store>, component: &str) -> Result<()> {
    let status = match store
        .map(|store| store.read_status())
        .transpose()?
        .flatten()
    {
        Some(bytes) => {
            let status: Status = serde_json::from_slice(&bytes)?;
            if status.schema_version != 1 || status.component != component || status.flash_enabled {
                return Err("Unsupported Mesa status record".into());
            }
            status
        }
        None => Status::new(component, "not_checked", "No Mesa operation has completed"),
    };
    print_status(&status)
}

pub(crate) fn check() -> Result<()> {
    let uid = platform::require_operator()?;
    let store = Store::user(uid, true)?.ok_or("Missing Mesa download cache")?;
    let _lock = store.lock()?;
    operation(&store, "mesa-update", || {
        let installed = platform::installed_version()?;
        check_with(&OfficialHttp::new()?, &installed)
    })
}

fn check_with(fetch: &impl Fetch, installed: &str) -> Result<Status> {
    let (app, mesa) = release::latest_pair(fetch)?;
    let paired = app == mesa.manifest.compatible_app_version;
    let mut status = if !paired {
        Status::new(
            "mesa-update",
            "version_mismatch",
            "Latest application and Mesa releases are not paired",
        )
    } else if !mesa.manifest.firmware.available {
        Status::new(
            "mesa-update",
            "source_only",
            "Paired source update is published; no verified firmware is available",
        )
    } else {
        Status::new("mesa-update", "release_available", "Paired verified firmware is published; download requires its application version to be installed")
    };
    status.installed_app_version = Some(installed.into());
    status.available_version = paired.then(|| app.clone());
    status.app_latest_version = Some(app);
    status.mesa_latest_version = Some(mesa.manifest.version.clone());
    status.manifest = Some(mesa.manifest);
    Ok(status)
}

pub(crate) fn download() -> Result<()> {
    let uid = platform::require_operator()?;
    let store = Store::user(uid, true)?.ok_or("Missing Mesa download cache")?;
    let _lock = store.lock()?;
    operation(&store, "mesa-update", || {
        let installed = platform::installed_version()?;
        verify_download(&OfficialHttp::new()?, &installed, false, |bytes| {
            store.write("firmware.bit", bytes)
        })
    })
}

pub(crate) fn apply_system() -> Result<()> {
    // This branch has no controller, systemctl or mesaflash command. A verified
    // bitstream is necessary but never sufficient to authorize flashing.
    platform::require_root()?;
    let cache = Store::root_cache()?;
    let _lock = cache.lock()?;
    let state = Store::root_state(true)?.ok_or("Missing Mesa flash state directory")?;
    operation(&state, "mesa-flash", || {
        let installed = platform::installed_version()?;
        verify_download(&OfficialHttp::new()?, &installed, true, |bytes| {
            cache.write("firmware.bit", bytes)
        })
    })?;
    Err("Mesa flashing is blocked; no approved hardware apply protocol is enabled".into())
}

fn verify_download(
    fetch: &impl Fetch,
    installed: &str,
    root: bool,
    mut save: impl FnMut(&[u8]) -> Result<()>,
) -> Result<Status> {
    // Both processes construct a fresh official release request. The root path
    // accepts neither a manifest nor a bitstream from the operating account.
    let release = release::installed_release(fetch, installed)?;
    let bytes = release::firmware(fetch, &release)?;
    let downloaded = if let Some(bytes) = bytes {
        save(&bytes)?;
        true
    } else {
        false
    };
    let (phase, message) = if root {
        if downloaded {
            ("blocked", "Root independently verified the download; the hardware apply protocol is not approved")
        } else {
            (
                "blocked",
                "No verified firmware exists for this application version; flashing is forbidden",
            )
        }
    } else if downloaded {
        (
            "downloaded",
            "Firmware hash and version verified in the user cache; the board has not been flashed",
        )
    } else {
        (
            "firmware_unavailable",
            "Source release exists, but there is no verified firmware to download or flash",
        )
    };
    let mut status = Status::new(
        if root { "mesa-flash" } else { "mesa-update" },
        phase,
        message,
    );
    status.installed_app_version = Some(installed.into());
    status.available_version = Some(release.manifest.version.clone());
    status.firmware_downloaded = downloaded;
    status.manifest = Some(release.manifest);
    Ok(status)
}

fn operation(store: &Store, component: &str, run: impl FnOnce() -> Result<Status>) -> Result<()> {
    let pending = Status::new(
        component,
        "checking",
        "Fetching official version-paired Mesa metadata",
    );
    store.write("status.json", &serde_json::to_vec(&pending)?)?;
    match run() {
        Ok(status) => {
            store.write("status.json", &serde_json::to_vec(&status)?)?;
            print_status(&status)
        }
        Err(error) => {
            let status = Status::new(component, "error", &error.to_string());
            store.write("status.json", &serde_json::to_vec(&status)?)?;
            print_status(&status)?;
            Err(error)
        }
    }
}

fn print_status(status: &Status) -> Result<()> {
    let mut stdout = std::io::stdout().lock();
    serde_json::to_writer(&mut stdout, status)?;
    writeln!(stdout)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::contract;
    use std::cell::RefCell;

    struct SourceRelease {
        calls: RefCell<Vec<String>>,
    }

    impl Fetch for SourceRelease {
        fn get(&self, url: &str, _limit: u64) -> Result<Vec<u8>> {
            self.calls.borrow_mut().push(url.into());
            let manifest = contract::fixture();
            if url.ends_with("/mesa-release.json") {
                return Ok(serde_json::to_vec(&manifest)?);
            }
            if url.contains("/git/ref/tags/") {
                return Ok(serde_json::to_vec(&serde_json::json!({
                    "object": {"type": "commit", "sha": manifest.source_commit},
                }))?);
            }
            if url.contains("/releases/") {
                let mut assets = vec![serde_json::json!({
                    "name": "mesa-release.json", "size": serde_json::to_vec(&manifest)?.len(),
                    "browser_download_url": "https://github.com/ArcAmberTeam/CNC-Mesa/releases/download/v26.10.26.1/mesa-release.json",
                })];
                for artifact in [&manifest.artifacts.source, &manifest.artifacts.integration] {
                    assets.push(serde_json::json!({
                        "name": artifact.asset, "size": artifact.size_bytes,
                        "browser_download_url": format!("https://github.com/ArcAmberTeam/CNC-Mesa/releases/download/v26.10.26.1/{}", artifact.asset),
                    }));
                }
                return Ok(serde_json::to_vec(&serde_json::json!({
                    "tag_name": "v26.10.26.1", "draft": false, "prerelease": false, "assets": assets,
                }))?);
            }
            Err("Unexpected network request".into())
        }
    }

    #[test]
    fn root_refetches_metadata_and_cannot_flash_a_source_only_release() {
        let fetch = SourceRelease {
            calls: RefCell::new(Vec::new()),
        };
        let user = verify_download(&fetch, "26.10.26.1", false, |_| {
            panic!("No firmware exists")
        })
        .unwrap();
        let user_calls = fetch.calls.borrow().len();
        let root =
            verify_download(&fetch, "26.10.26.1", true, |_| panic!("No firmware exists")).unwrap();
        assert_eq!(fetch.calls.borrow().len(), user_calls * 2);
        assert_eq!(user.phase, "firmware_unavailable");
        assert_eq!(root.phase, "blocked");
        assert!(!root.flash_enabled);
        assert!(!root.firmware_downloaded);
        let check = check_with(&fetch, "26.10.25.1").unwrap();
        assert_eq!(check.phase, "source_only");
        assert_eq!(check.available_version.as_deref(), Some("26.10.26.1"));
    }
}
