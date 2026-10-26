//! Standalone homing intent; only Controller may command the machine.
use super::{
    config::Options,
    control,
    protocol::{canonical_id, params, Error, Result},
};
use serde_json::Value;
use std::time::Duration;

pub(super) async fn request(options: &Options, method: &str, p: Value) -> Result<Value> {
    let local = match method {
        "home.start" => {
            params(&p, &["operationId", "clearanceConfirmed"])?;
            if p["clearanceConfirmed"] != true {
                return Err(Error::new(
                    "invalid_params",
                    "confirm the homing clearance first",
                ));
            }
            if !options.auto_run {
                return Err(Error::new("auto_run_disabled", "CAM motion is disabled"));
            }
            "cam.home.start"
        }
        "home.status" => {
            params(&p, &["operationId"])?;
            "cam.home.status"
        }
        "home.cancel" => {
            params(&p, &["operationId"])?;
            "cam.home.cancel"
        }
        _ => {
            return Err(Error::new(
                "unsupported_method",
                "unsupported homing method",
            ))
        }
    };
    if !p["operationId"].as_str().is_some_and(canonical_id) {
        return Err(Error::new(
            "invalid_params",
            "operationId must be a lowercase UUID",
        ));
    }
    control::once(&options.control_socket, local, p, Duration::from_secs(10)).await
}
