//! File reception only: no control connection and no motion side effects.
use super::{
    inbox::{Inbox, Upload},
    protocol::{params, Error, Result},
};
use serde_json::{json, Value};

#[derive(Default)]
pub(super) struct Transfer {
    active: Option<Upload>,
}

async fn storage<T: Send + 'static>(
    work: impl FnOnce() -> Result<T> + Send + 'static,
) -> Result<T> {
    tokio::task::spawn_blocking(work)
        .await
        .map_err(|_| Error::new("storage_unavailable", "inbox worker failed"))?
        .map_err(|e| {
            if e.code == "io_error" {
                Error::new("storage_unavailable", "inbox I/O failed")
            } else {
                e
            }
        })
}
pub(super) async fn receipt(inbox: &Inbox, id: Value) -> Result<Value> {
    let inbox = inbox.clone();
    storage(move || inbox.receipt(&id)).await
}

impl Transfer {
    pub async fn request(&mut self, inbox: &Inbox, method: &str, p: Value) -> Result<Value> {
        match method {
            "upload.begin" => {
                params(&p, &["transferId", "filename", "size", "sha256"])?;
                if self.active.is_some() {
                    return Err(Error::new(
                        "upload_in_progress",
                        "finish or abort the current upload",
                    ));
                }
                let inbox = inbox.clone();
                self.active = Some(storage(move || inbox.begin(&p)).await?);
                Ok(json!({"state":"receiving","nextOffset":0}))
            }
            "upload.chunk" => {
                let mut upload = self
                    .active
                    .take()
                    .ok_or_else(|| Error::new("no_upload", "begin an upload first"))?;
                params(&p, &["offset", "data"])?;
                let (upload, result) = storage(move || {
                    let result = upload.write(&p)?;
                    Ok((upload, result))
                })
                .await?;
                self.active = Some(upload);
                Ok(result)
            }
            "upload.finish" => {
                let upload = self
                    .active
                    .take()
                    .ok_or_else(|| Error::new("no_upload", "begin an upload first"))?;
                params(&p, &[])?;
                let inbox = inbox.clone();
                let result = storage(move || inbox.finish(upload)).await?;
                Ok(result)
            }
            "upload.abort" => {
                params(&p, &[])?;
                self.active = None;
                Ok(json!({"aborted":true}))
            }
            "upload.receipt" => {
                params(&p, &["transferId"])?;
                receipt(inbox, p["transferId"].clone()).await
            }
            _ => Err(Error::new(
                "unsupported_method",
                "unsupported transfer method",
            )),
        }
    }
}
