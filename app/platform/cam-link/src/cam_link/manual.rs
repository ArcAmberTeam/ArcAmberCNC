use super::{
    control,
    protocol::{canonical_id, params, Error, Result},
};
use serde_json::{json, Value};
use std::{
    collections::HashSet,
    path::{Path, PathBuf},
    time::Duration,
};
use tokio::{
    net::UnixStream,
    sync::{mpsc, oneshot},
    task::JoinHandle,
    time::{timeout_at, Instant},
};
const LEASE: Duration = Duration::from_millis(450);
type Renewal = oneshot::Sender<Result<()>>;
struct Active {
    id: String,
    renew: mpsc::Sender<Renewal>,
    task: JoinHandle<()>,
}
impl Drop for Active {
    fn drop(&mut self) {
        self.task.abort();
    }
}
#[derive(Default)]
pub(super) struct Jog {
    active: Option<Active>,
    used: HashSet<String>,
}
impl Jog {
    pub async fn request(&mut self, path: &Path, method: &str, p: Value) -> Result<Value> {
        params(
            &p,
            if method == "jog.start" {
                &["jogId", "axis", "direction", "feedRate"]
            } else {
                &["jogId"]
            },
        )?;
        let id = p["jogId"]
            .as_str()
            .filter(|s| canonical_id(s))
            .ok_or_else(|| Error::new("invalid_params", "jogId must be a canonical UUID"))?
            .to_owned();
        let accepted = json!({"jogId":id,"accepted":true});
        if method == "jog.stop" {
            if self.active.as_ref().is_some_and(|a| a.id == id) {
                self.active = None;
            }
            if self.used.len() < 2048 {
                self.used.insert(id);
            }
            return Ok(accepted);
        }
        if method == "jog.keepalive" {
            if let Some(active) = &self.active {
                let (tx, rx) = oneshot::channel();
                if active.id == id
                    && active.renew.try_send(tx).is_ok()
                    && rx.await.is_ok_and(|r| r.is_ok())
                {
                    return Ok(accepted);
                }
            }
            self.active = None;
            return Err(Error::new(
                "jog_expired",
                "jog ended; press again to start a new movement",
            ));
        }
        if self.active.as_ref().is_some_and(|a| !a.task.is_finished())
            || self.used.contains(&id)
            || self.used.len() >= 2048
        {
            return Err(Error::new(
                "jog_busy",
                "movement active or jogId already used",
            ));
        }
        if !matches!(p["axis"].as_str(), Some("X" | "Y" | "Z"))
            || !matches!(p["direction"].as_i64(), Some(-1 | 1))
            || !p["feedRate"].as_f64().is_some_and(|v| v > 0. && v <= 3000.)
        {
            return Err(Error::new(
                "invalid_params",
                "invalid axis, direction or feed rate",
            ));
        }
        self.used.insert(id.clone());
        let (ready_tx, ready_rx) = oneshot::channel();
        let (tx, rx) = mpsc::channel(1);
        let task = tokio::spawn(lease(path.to_owned(), p, ready_tx, rx));
        self.active = Some(Active {
            id,
            renew: tx,
            task,
        });
        let result = ready_rx.await.unwrap_or_else(|_| {
            Err(Error::new(
                "controller_unavailable",
                "cannot establish continuous jog",
            ))
        });
        if let Err(error) = result {
            self.active = None;
            return Err(error);
        }
        Ok(accepted)
    }
}
async fn lease(
    path: PathBuf,
    p: Value,
    ready: oneshot::Sender<Result<()>>,
    mut renew: mpsc::Receiver<Renewal>,
) {
    let mut deadline = Instant::now() + LEASE;
    let result = timeout_at(deadline, async {
        let mut stream = UnixStream::connect(path).await?;
        let result = control::request(&mut stream, "cam.jog.start", p.clone()).await?;
        if result["accepted"] != true {
            return Err(Error::new(
                "jog_rejected",
                "controller rejected continuous jog",
            ));
        }
        Ok(stream)
    })
    .await;
    let mut stream = match result {
        Ok(Ok(stream)) => stream,
        other => {
            let _ = ready.send(Err(match other {
                Ok(Err(e)) if e.code != "io_error" => e,
                _ => Error::new("controller_unavailable", "cannot establish continuous jog"),
            }));
            return;
        }
    };
    if ready.send(Ok(())).is_err() {
        return;
    }
    loop {
        // The old deadline bounds both waiting for renewal and its controller ACK.
        // EOF on expiry revokes only this owner, even while TCP is stalled.
        let result = timeout_at(deadline, async {
            let reply = renew.recv().await?;
            let result = control::request(
                &mut stream,
                "cam.jog.keepalive",
                json!({"jogId":p["jogId"]}),
            )
            .await;
            let valid = result.as_ref().is_ok_and(|v| v["accepted"] == true);
            let _ = reply.send(if valid {
                Ok(())
            } else {
                Err(Error::new("jog_expired", "controller lease renewal failed"))
            });
            valid.then_some(())
        })
        .await;
        if !matches!(result, Ok(Some(()))) {
            return;
        }
        deadline = Instant::now() + LEASE;
    }
}
