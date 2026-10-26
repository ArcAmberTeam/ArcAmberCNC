use super::protocol::{canonical_id, Error, Result};
use clap::Parser;
use std::{
    fs,
    net::{IpAddr, Ipv4Addr},
    os::unix::fs::MetadataExt,
    path::PathBuf,
    sync::Arc,
    time::Duration,
};
use tokio_rustls::{rustls::ServerConfig, TlsAcceptor};

#[derive(Parser, Debug)]
#[command(about = "Rust CAM Link system service: TCP reception, UDP discovery and local control")]
pub(super) struct Options {
    #[arg(long)]
    pub inbox: PathBuf,
    #[arg(long)]
    pub control_socket: PathBuf,
    #[arg(long, default_value = "127.0.0.1")]
    pub host: IpAddr,
    #[arg(long, default_value_t = 6522)]
    pub port: u16,
    #[arg(long, default_value_t = 67108864)]
    pub max_bytes: u64,
    #[arg(long, default_value_t = 60.0)]
    pub idle_timeout: f64,
    #[arg(long, default_value_t = 10.0)]
    pub io_timeout: f64,
    #[arg(long)]
    pub token_file: Option<PathBuf>,
    #[arg(long, requires = "key")]
    pub cert: Option<PathBuf>,
    #[arg(long, requires = "cert")]
    pub key: Option<PathBuf>,
    #[arg(long)]
    /// Allow explicit CAM home/job/workflow starts; uploads never start motion.
    pub auto_run: bool,
    #[arg(long, requires = "device_id")]
    pub discover: bool,
    #[arg(long)]
    pub device_id: Option<String>,
    #[arg(long, default_value = "LinuxCNC")]
    pub device_name: String,
    #[arg(long, default_value = "255.255.255.255")]
    pub discovery_address: Ipv4Addr,
    #[arg(long, default_value_t = 8421)]
    pub discovery_port: u16,
    #[arg(long)]
    pub discovery_bind_port: Option<u16>,
    #[arg(long, default_value_t = 3.0)]
    pub discovery_interval: f64,
}
pub(super) fn duration(value: f64) -> Result<Duration> {
    Duration::try_from_secs_f64(value)
        .ok()
        .filter(|v| !v.is_zero())
        .ok_or_else(|| Error::new("configuration", "timeouts must be positive and finite"))
}
impl Options {
    pub fn validate(&self) -> Result<()> {
        duration(self.io_timeout)?;
        duration(self.idle_timeout)?;
        if self.max_bytes == 0 {
            return Err(Error::new("configuration", "max_bytes must be positive"));
        }
        if self.discover {
            if !self.device_id.as_deref().is_some_and(canonical_id)
                || !(1..=64).contains(&self.device_name.chars().count())
                || self.device_name.chars().any(|c| c < ' ' || c == '\u{7f}')
            {
                return Err(Error::new(
                    "configuration",
                    "discovery requires a lowercase UUID and printable device name",
                ));
            }
            if !self.host.is_ipv4()
                || (self.host.is_loopback() && !self.discovery_address.is_loopback())
            {
                return Err(Error::new(
                    "configuration",
                    "LAN discovery needs --host 0.0.0.0 or a LAN IPv4 address",
                ));
            }
            if self.discovery_port == 0
                || !self.discovery_interval.is_finite()
                || !(0.1..=60.).contains(&self.discovery_interval)
            {
                return Err(Error::new(
                    "configuration",
                    "discovery port must be nonzero; interval must be 0.1 to 60 seconds",
                ));
            }
        }
        Ok(())
    }
    pub fn token(&self) -> Result<Option<Vec<u8>>> {
        self.token_file
            .as_ref()
            .map(|path| {
                let info = fs::symlink_metadata(path)?;
                if !info.is_file()
                    || info.uid() != unsafe { libc::getuid() }
                    || info.mode() & 0o077 != 0
                    || info.len() > 257
                {
                    return Err(Error::new(
                        "configuration",
                        "token file must be user-owned, mode 0600, and at most 257 bytes",
                    ));
                }
                let token = fs::read_to_string(path)?.trim().as_bytes().to_vec();
                if !(32..=256).contains(&token.len())
                    || !token
                        .iter()
                        .all(|b| b.is_ascii_alphanumeric() || *b == b'_' || *b == b'-')
                {
                    return Err(Error::new(
                        "configuration",
                        "token must contain 32 to 256 URL-safe characters",
                    ));
                }
                Ok(token)
            })
            .transpose()
    }
    pub fn tls(&self) -> Result<Option<TlsAcceptor>> {
        self.cert
            .as_ref()
            .map(|cert| {
                let certs = rustls_pemfile::certs(&mut fs::read(cert)?.as_slice())
                    .collect::<std::io::Result<Vec<_>>>()?;
                let key = rustls_pemfile::private_key(
                    &mut fs::read(self.key.as_ref().unwrap())?.as_slice(),
                )?
                .ok_or_else(|| Error::new("configuration", "missing TLS private key"))?;
                let config = ServerConfig::builder()
                    .with_no_client_auth()
                    .with_single_cert(certs, key)
                    .map_err(|e| {
                        Error::new(
                            "configuration",
                            &format!("invalid TLS certificate or key: {e}"),
                        )
                    })?;
                Ok(TlsAcceptor::from(Arc::new(config)))
            })
            .transpose()
    }
}
