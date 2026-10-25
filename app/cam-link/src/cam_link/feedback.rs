use super::{
    control,
    inbox::Inbox,
    protocol::{self, Error, Result},
};
use serde_json::{json, Value};
use std::{path::Path, time::Duration};
use tokio::{
    io::{AsyncWrite, AsyncWriteExt},
    sync::{mpsc, oneshot, watch},
    task::JoinHandle,
};

pub(super) struct Task(pub JoinHandle<()>);
impl Task {
    pub async fn stop(mut self) {
        self.0.abort();
        let _ = (&mut self.0).await;
    }
}
impl Drop for Task {
    fn drop(&mut self) {
        self.0.abort();
    }
}

pub(super) struct Outbound {
    frame: Option<(&'static str, Value)>,
    acknowledged: oneshot::Sender<Result<()>>,
}
pub(super) type Writer = mpsc::Sender<Outbound>;

pub(super) fn channel<W: AsyncWrite + Unpin + Send + 'static>(
    mut writer: W,
    io: Duration,
    failed: watch::Sender<bool>,
) -> (Writer, Task) {
    let (sender, mut queue) = mpsc::channel::<Outbound>(4);
    let task = tokio::spawn(async move {
        while let Some(message) = queue.recv().await {
            // The writer owns the complete frame. Cancelling a subscription or
            // request waiter cannot truncate a frame already being sent.
            let result = match message.frame {
                Some((kind, value)) => protocol::write(&mut writer, kind, &value, io).await,
                None => match tokio::time::timeout(io, writer.shutdown()).await {
                    Ok(result) => result.map_err(Error::from),
                    Err(error) => Err(error.into()),
                },
            };
            let broken = result.is_err();
            let _ = message.acknowledged.send(result);
            if broken {
                let _ = failed.send(true);
                return;
            }
        }
    });
    (sender, Task(task))
}

async fn enqueue(
    writer: &Writer,
    frame: Option<(&'static str, Value)>,
    io: Duration,
) -> Result<()> {
    tokio::time::timeout(io, async {
        let (acknowledged, received) = oneshot::channel();
        writer
            .send(Outbound {
                frame,
                acknowledged,
            })
            .await
            .map_err(|_| Error::new("io_error", "writer closed"))?;
        received
            .await
            .map_err(|_| Error::new("io_error", "writer closed"))?
    })
    .await?
}

pub(super) async fn send(
    writer: &Writer,
    kind: &'static str,
    value: &Value,
    io: Duration,
) -> Result<()> {
    enqueue(writer, Some((kind, value.clone())), io).await
}

pub(super) async fn shutdown(writer: &Writer, io: Duration) -> Result<()> {
    enqueue(writer, None, io).await
}

pub(super) async fn status(path: &Path, inbox: &Inbox) -> Result<Value> {
    let mut value =
        control::once(path, "machine.status", json!({}), Duration::from_secs(2)).await?;
    let inbox = inbox.clone();
    let file = value["file"].clone();
    if let Ok(Some(id)) = tokio::task::spawn_blocking(move || inbox.identify(&file)).await {
        value["transferId"] = id;
    } else if value.get("transferId").is_none() {
        value["transferId"] = Value::Null;
    }
    Ok(value)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::io::AsyncReadExt;

    #[tokio::test]
    async fn cancelling_a_subscriber_does_not_truncate_its_in_flight_frame() {
        let (output, mut client) = tokio::io::duplex(32);
        let (failed, failure) = watch::channel(false);
        let (writer, _task) = channel(output, Duration::from_secs(2), failed);
        let event = json!({"version":2,"event":"machine.status","data":"x".repeat(1024)});
        let cancelled = tokio::spawn({
            let writer = writer.clone();
            let event = event.clone();
            async move { send(&writer, "STATUS", &event, Duration::from_secs(2)).await }
        });
        // Read the beginning of a frame while its remaining bytes face backpressure.
        let mut header = [0; 24];
        client.read_exact(&mut header).await.unwrap();
        cancelled.abort();
        let _ = cancelled.await;
        let reply = json!({"version":2,"requestId":"stop","result":{"subscribed":false}});
        let next = tokio::spawn({
            let writer = writer.clone();
            let reply = reply.clone();
            async move { send(&writer, "REPLY", &reply, Duration::from_secs(2)).await }
        });
        let (_, size) = protocol::header(&header).unwrap();
        let mut body = vec![0; size];
        client.read_exact(&mut body).await.unwrap();
        assert_eq!(protocol::json_bytes(&body).unwrap(), event);
        client.read_exact(&mut header).await.unwrap();
        let (kind, size) = protocol::header(&header).unwrap();
        assert_eq!(kind, "REPLY");
        let mut body = vec![0; size];
        client.read_exact(&mut body).await.unwrap();
        assert_eq!(protocol::json_bytes(&body).unwrap(), reply);
        next.await.unwrap().unwrap();
        assert!(!*failure.borrow());
    }
}
