use super::{
    config::Options,
    control,
    feedback::{self, Task, Writer},
    inbox::{Inbox, Upload},
    manual::Jog,
    protocol::{self, params, Error, Result},
};
use serde_json::{json, Value};
use std::{collections::HashSet, sync::Arc, time::Duration};
use subtle::ConstantTimeEq;
use tokio::{
    io::{AsyncRead, AsyncWrite},
    sync::watch,
};

pub(super) struct Service {
    pub options: Options,
    pub token: Option<Vec<u8>>,
    pub inbox: Inbox,
    pub io: Duration,
    pub idle: Duration,
}
struct Session {
    service: Arc<Service>,
    writer: Writer,
    _output: Task,
    upload: Option<Upload>,
    jog: Jog,
    subscription: Option<Task>,
    failed: watch::Sender<bool>,
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
impl Session {
    async fn route(&mut self, method: &str, p: Value) -> Result<Value> {
        let service = &self.service;
        match method {
            "jog.start" | "jog.keepalive" | "jog.stop" => {
                self.jog
                    .request(&service.options.control_socket, method, p)
                    .await
            }
            "ping" => {
                params(&p, &[])?;
                Ok(json!({"alive":true}))
            }
            "upload.begin" => {
                params(&p, &["transferId", "filename", "size", "sha256"])?;
                if self.upload.is_some() {
                    return Err(Error::new(
                        "upload_in_progress",
                        "finish or abort the current upload",
                    ));
                }
                let inbox = service.inbox.clone();
                self.upload = Some(storage(move || inbox.begin(&p)).await?);
                Ok(json!({"state":"receiving","nextOffset":0}))
            }
            "upload.chunk" => {
                let mut upload = self
                    .upload
                    .take()
                    .ok_or_else(|| Error::new("no_upload", "begin an upload first"))?;
                params(&p, &["offset", "data"])?;
                let (upload, result) = storage(move || {
                    let result = upload.write(&p)?;
                    Ok((upload, result))
                })
                .await?;
                self.upload = Some(upload);
                Ok(result)
            }
            "upload.finish" => {
                let upload = self
                    .upload
                    .take()
                    .ok_or_else(|| Error::new("no_upload", "begin an upload first"))?;
                params(&p, &[])?;
                let inbox = service.inbox.clone();
                let mut result = storage(move || inbox.finish(upload)).await?;
                if service.options.auto_run {
                    let method = if result["duplicate"] == true {
                        "cam.job.status"
                    } else {
                        "cam.job.start"
                    };
                    result["job"] = match control::job(
                        &service.options.control_socket,
                        method,
                        result["transferId"].clone(),
                    )
                    .await
                    {
                        Ok(job) => job,
                        Err(error) => {
                            json!({"transferId":result["transferId"],"state":if error.code=="controller_unavailable"{"unknown"}else{"error"},"message":error.message})
                        }
                    };
                }
                Ok(result)
            }
            "upload.abort" => {
                params(&p, &[])?;
                self.upload = None;
                Ok(json!({"aborted":true}))
            }
            "upload.receipt" | "job.start" | "job.status" => {
                params(&p, &["transferId"])?;
                if method.starts_with("job.") && !service.options.auto_run {
                    return Err(Error::new(
                        "auto_run_disabled",
                        "CAM auto execution is disabled",
                    ));
                }
                let inbox = service.inbox.clone();
                let id = p["transferId"].clone();
                let mut receipt = storage(move || inbox.receipt(&id)).await?;
                if service.options.auto_run {
                    let local = if method == "job.start" {
                        "cam.job.start"
                    } else {
                        "cam.job.status"
                    };
                    let job = control::job(
                        &service.options.control_socket,
                        local,
                        p["transferId"].clone(),
                    )
                    .await?;
                    if method.starts_with("job.") {
                        return Ok(json!({"job":job}));
                    }
                    receipt["job"] = job;
                }
                Ok(receipt)
            }
            "status.get" => {
                params(&p, &[])?;
                feedback::status(&service.options.control_socket, &service.inbox).await
            }
            "status.subscribe" => {
                params(&p, &["interval"])?;
                if !p["interval"]
                    .as_f64()
                    .is_some_and(|v| (1.0..=60.).contains(&v))
                {
                    return Err(Error::new(
                        "invalid_params",
                        "interval must be 1 to 60 seconds",
                    ));
                }
                // Abort before taking the writer lock; no old events after the ACK.
                self.unsubscribe().await;
                Ok(json!({"subscribed":true,"interval":p["interval"]}))
            }
            "status.unsubscribe" => {
                params(&p, &[])?;
                self.unsubscribe().await;
                Ok(json!({"subscribed":false}))
            }
            _ => Err(Error::new(
                "unsupported_method",
                "unsupported CAM Link method",
            )),
        }
    }
    async fn unsubscribe(&mut self) {
        if let Some(task) = self.subscription.take() {
            task.stop().await;
        }
    }
    fn subscribe(&mut self, interval: f64) {
        let service = self.service.clone();
        let writer = self.writer.clone();
        let failed = self.failed.clone();
        self.subscription = Some(Task(tokio::spawn(async move {
            loop {
                let mut event = json!({"version":2,"event":"machine.status"});
                match feedback::status(&service.options.control_socket, &service.inbox).await {
                    Ok(status) => event["data"] = status,
                    Err(error) => event["error"] = error.wire(),
                }
                if feedback::send(&writer, "STATUS", &event, service.io)
                    .await
                    .is_err()
                {
                    let _ = failed.send(true);
                    return;
                }
                tokio::time::sleep(Duration::from_secs_f64(interval)).await;
            }
        })));
    }
}
pub(super) async fn run<S: AsyncRead + AsyncWrite + Unpin + Send + 'static>(
    stream: S,
    service: Arc<Service>,
) -> Result<()> {
    let (reader, writer) = tokio::io::split(stream);
    let mut reader = tokio::io::BufReader::with_capacity(protocol::MAX_FRAME + 24, reader);
    let (failed, mut failure) = watch::channel(false);
    let (writer, output) = feedback::channel(writer, service.io, failed.clone());
    let mut session = Session {
        service: service.clone(),
        writer,
        _output: output,
        upload: None,
        jog: Jog::default(),
        subscription: None,
        failed,
    };
    let mut authenticated = false;
    let mut ids = HashSet::new();
    loop {
        let request = tokio::select! {
            _=failure.changed()=>return Ok(()),
            request=protocol::read(&mut reader,if authenticated{service.idle}else{service.io},service.io)=>request,
        };
        let request = match request {
            Ok(request) => request,
            Err(error) => {
                if !matches!(error.code.as_str(), "io_error" | "timeout") {
                    feedback::send(
                        &session.writer,
                        "ERROR",
                        &json!({"version":2,"requestId":error.request_id,"error":error.wire()}),
                        service.io,
                    )
                    .await?;
                }
                session.jog = Jog::default();
                session.upload = None;
                session.unsubscribe().await;
                // Send FIN before discarding an invalid frame's unread body. This
                // preserves the error receipt instead of resetting TCP immediately.
                let _ = feedback::shutdown(&session.writer, service.io).await;
                return Ok(());
            }
        };
        let duplicate = ids.contains(&request.id);
        let limit = ids.len() >= 100000;
        let result = if duplicate {
            Err(Error::new("duplicate_request", "requestId was used"))
        } else if limit {
            Err(Error::new("session_limit", "reconnect to continue"))
        } else {
            ids.insert(request.id.clone());
            if !authenticated {
                let valid = request.method == "session.auth"
                    && match &service.token {
                        None => request.params == json!({}),
                        Some(token) => {
                            params(&request.params, &["token"]).is_ok()
                                && request.params["token"]
                                    .as_str()
                                    .is_some_and(|s| bool::from(s.as_bytes().ct_eq(token)))
                        }
                    };
                if valid {
                    authenticated = true;
                    Ok(json!({"authenticated":true}))
                } else {
                    Err(Error::new("unauthorized", "authenticate first"))
                }
            } else {
                session.route(&request.method, request.params).await
            }
        };
        match result {
            Ok(result) => {
                feedback::send(
                    &session.writer,
                    "REPLY",
                    &json!({"version":2,"requestId":request.id,"result":result}),
                    service.io,
                )
                .await?;
                if request.method == "status.subscribe" {
                    session.subscribe(result["interval"].as_f64().unwrap());
                }
            }
            Err(error) => {
                if matches!(request.method.as_str(), "upload.chunk" | "upload.finish") && !duplicate
                {
                    session.upload = None;
                }
                feedback::send(
                    &session.writer,
                    "ERROR",
                    &json!({"version":2,"requestId":request.id,"error":error.wire()}),
                    service.io,
                )
                .await?;
            }
        }
        if !authenticated || limit {
            return Ok(());
        }
    }
}
