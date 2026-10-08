//! Local v1 diagnostics transport; no desktop runtime or machine control.

mod service;

pub use service::{probe_service, ServiceHealth};
