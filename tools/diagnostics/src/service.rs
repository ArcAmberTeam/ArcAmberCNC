use serde::{Deserialize, Serialize};
use std::path::Path;
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::UnixStream;

const MAX_FRAME_BYTES: usize = 65536;

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ServiceHealth {
    pub service: String,
    pub mode: String,
    pub machine_connected: bool,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Reply {
    version: u32,
    request_id: String,
    result: ServiceHealth,
}

/// Probe the local diagnostics protocol; this API cannot send machine commands.
pub async fn probe_service(path: &Path) -> Result<ServiceHealth, String> {
    tokio::time::timeout(Duration::from_secs(2), exchange(path))
        .await
        .map_err(|_| "本地服务响应超时".to_string())?
}

async fn exchange(path: &Path) -> Result<ServiceHealth, String> {
    let mut stream = UnixStream::connect(path)
        .await
        .map_err(|_| "本地服务未启动或无法连接".to_string())?;
    let request = br#"{"version":1,"request_id":"desktop-health","method":"health"}"#;
    stream
        .write_u32(request.len() as u32)
        .await
        .map_err(|_| "本地服务连接中断".to_string())?;
    stream
        .write_all(request)
        .await
        .map_err(|_| "本地服务连接中断".to_string())?;
    let size = stream
        .read_u32()
        .await
        .map_err(|_| "本地服务响应不完整".to_string())? as usize;
    if size == 0 || size > MAX_FRAME_BYTES {
        return Err("本地服务响应长度无效".into());
    }
    let mut body = vec![0; size];
    stream
        .read_exact(&mut body)
        .await
        .map_err(|_| "本地服务响应不完整".to_string())?;
    let reply: Reply =
        serde_json::from_slice(&body).map_err(|_| "本地服务协议不匹配".to_string())?;
    if reply.version != 1
        || reply.request_id != "desktop-health"
        || reply.result.service != "betterlinuxcnc"
        || reply.result.mode != "diagnostics-only"
        || reply.result.machine_connected
    {
        return Err("本地服务协议不匹配".into());
    }
    Ok(reply.result)
}
