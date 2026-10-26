//! Submit a verified transfer to the Controller-owned home-then-run workflow.
use super::{
    config::Options,
    control,
    inbox::Inbox,
    protocol::{params, Error, Result},
    transfer,
};
use serde_json::Value;
use std::time::Duration;

pub(super) async fn request(
    options: &Options,
    inbox: &Inbox,
    method: &str,
    p: Value,
) -> Result<Value> {
    let local = match method {
        "workflow.start" => {
            params(
                &p,
                &["transferId", "clearanceConfirmed", "machiningConfirmed"],
            )?;
            if p["clearanceConfirmed"] != true || p["machiningConfirmed"] != true {
                return Err(Error::new(
                    "invalid_params",
                    "confirm clearance and machining setup first",
                ));
            }
            "cam.workflow.start"
        }
        "job.start" => {
            params(&p, &["transferId"])?;
            "cam.job.start"
        }
        "job.status" | "workflow.status" => {
            params(&p, &["transferId"])?;
            "cam.job.status"
        }
        "job.cancel" | "workflow.cancel" => {
            params(&p, &["transferId"])?;
            "cam.job.cancel"
        }
        _ => {
            return Err(Error::new(
                "unsupported_method",
                "unsupported workflow method",
            ))
        }
    };
    if method.ends_with(".start") && !options.auto_run {
        return Err(Error::new("auto_run_disabled", "CAM execution is disabled"));
    }
    transfer::receipt(inbox, p["transferId"].clone()).await?;
    // Never poll a home result here and independently issue RUN: the Controller
    // owns the whole sequence, including cancellation and durable deduplication.
    control::once(&options.control_socket, local, p, Duration::from_secs(10)).await
}
