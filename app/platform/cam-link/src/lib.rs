//! Independently launched system services. LinuxCNC commands remain owned by the
//! local Controller, accessed exclusively through its public Unix protocol.
mod cam_link;

/// Run the installed CAM Link CLI until SIGINT or SIGTERM.
pub async fn run() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    cam_link::run().await
}
