mod service;

pub use service::{probe_service, ServiceHealth};

#[tauri::command]
async fn service_health() -> Result<ServiceHealth, String> {
    // The webview cannot choose a socket path or an arbitrary backend method.
    probe_service(&service::socket_path()).await
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![service_health])
        .run(tauri::generate_context!())
        .expect("failed to run BetterLinuxCNC desktop");
}
