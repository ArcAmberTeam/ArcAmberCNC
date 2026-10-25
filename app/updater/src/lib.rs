//! Verified, independently launched Debian Release updates.
mod updater;

/// Run the public release updater CLI.
pub fn run() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    updater::run()
}
