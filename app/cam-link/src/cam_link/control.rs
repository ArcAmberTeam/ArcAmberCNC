use super::protocol::{json_bytes, Error, Result, MAX_FRAME};
use serde_json::{json, Value};
use std::{path::Path, time::Duration};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::UnixStream,
    time::timeout,
};

pub(super) async fn request(stream: &mut UnixStream, method: &str, params: Value) -> Result<Value> {
    let id = uuid::Uuid::new_v4().to_string();
    let body =
        serde_json::to_vec(&json!({"version":2,"request_id":id,"method":method,"params":params}))
            .unwrap();
    stream.write_all(&(body.len() as u32).to_be_bytes()).await?;
    stream.write_all(&body).await?;
    let size = stream.read_u32().await? as usize;
    if !(1..=MAX_FRAME).contains(&size) {
        return Err(Error::new("invalid_response", "invalid local frame"));
    }
    let mut body = vec![0; size];
    stream.read_exact(&mut body).await?;
    let reply = json_bytes(&body)?;
    if reply["version"].as_u64() != Some(2) || reply["request_id"] != id {
        return Err(Error::new("invalid_response", "invalid local response"));
    }
    if let Some(error) = reply.get("error") {
        return Err(Error::new(
            error["code"].as_str().unwrap_or("controller_rejected"),
            error["message"]
                .as_str()
                .unwrap_or("controller rejected request"),
        ));
    }
    if !reply["result"].is_object() {
        return Err(Error::new("invalid_response", "missing local result"));
    }
    Ok(reply["result"].clone())
}
pub(super) async fn once(
    path: &Path,
    method: &str,
    params: Value,
    duration: Duration,
) -> Result<Value> {
    let result = timeout(duration, async {
        request(&mut UnixStream::connect(path).await?, method, params).await
    })
    .await;
    match result {
        Ok(Ok(v)) => Ok(v),
        Ok(Err(e))
            if !matches!(
                e.code.as_str(),
                "io_error" | "invalid_response" | "invalid_request"
            ) =>
        {
            Err(e)
        }
        _ => Err(Error::new(
            "controller_unavailable",
            "local controller unavailable; command outcome unknown, do not retry automatically",
        )),
    }
}
pub(super) async fn job(path: &Path, method: &str, id: Value) -> Result<Value> {
    let result = once(
        path,
        method,
        json!({"transferId":id}),
        Duration::from_secs(10),
    )
    .await?;
    result
        .get("job")
        .cloned()
        .ok_or_else(|| Error::new("controller_unavailable", "invalid local job result"))
}
