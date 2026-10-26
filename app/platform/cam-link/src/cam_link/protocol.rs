use serde::{
    de::{self, MapAccess, SeqAccess, Visitor},
    Deserialize, Deserializer,
};
use serde_json::{json, Map, Value};
use std::{fmt, io, time::Duration};
use tokio::io::{AsyncRead, AsyncReadExt, AsyncWrite, AsyncWriteExt};
use tokio::time::timeout;

pub(super) const MAX_FRAME: usize = 65536;
pub(super) type Result<T> = std::result::Result<T, Error>;

#[derive(Debug)]
pub(super) struct Error {
    pub code: String,
    pub message: String,
    pub request_id: String,
}
impl Error {
    pub fn new(code: &str, message: &str) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
            request_id: String::new(),
        }
    }
    pub fn wire(&self) -> Value {
        json!({"code":self.code,"message":self.message})
    }
}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.message)
    }
}
impl std::error::Error for Error {}
impl From<io::Error> for Error {
    fn from(_: io::Error) -> Self {
        Self::new("io_error", "connection or storage unavailable")
    }
}
impl From<tokio::time::error::Elapsed> for Error {
    fn from(_: tokio::time::error::Elapsed) -> Self {
        Self::new("timeout", "operation timed out")
    }
}

// serde_json::Value normally accepts duplicate keys. Reject them at every depth.
struct Unique(Value);
impl<'de> Deserialize<'de> for Unique {
    fn deserialize<D: Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
        struct JsonVisitor;
        impl<'de> Visitor<'de> for JsonVisitor {
            type Value = Unique;
            fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str("JSON with unique fields")
            }
            fn visit_bool<E: de::Error>(self, v: bool) -> std::result::Result<Unique, E> {
                Ok(Unique(v.into()))
            }
            fn visit_i64<E: de::Error>(self, v: i64) -> std::result::Result<Unique, E> {
                Ok(Unique(v.into()))
            }
            fn visit_u64<E: de::Error>(self, v: u64) -> std::result::Result<Unique, E> {
                Ok(Unique(v.into()))
            }
            fn visit_f64<E: de::Error>(self, v: f64) -> std::result::Result<Unique, E> {
                serde_json::Number::from_f64(v)
                    .map(|v| Unique(v.into()))
                    .ok_or_else(|| E::custom("nonfinite number"))
            }
            fn visit_str<E: de::Error>(self, v: &str) -> std::result::Result<Unique, E> {
                Ok(Unique(v.into()))
            }
            fn visit_unit<E: de::Error>(self) -> std::result::Result<Unique, E> {
                Ok(Unique(Value::Null))
            }
            fn visit_seq<A: SeqAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Unique, A::Error> {
                let mut items = Vec::new();
                while let Some(Unique(v)) = a.next_element()? {
                    items.push(v);
                }
                Ok(Unique(items.into()))
            }
            fn visit_map<A: MapAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Unique, A::Error> {
                let mut items = Map::new();
                while let Some((k, Unique(v))) = a.next_entry::<String, Unique>()? {
                    if items.insert(k, v).is_some() {
                        return Err(de::Error::custom("duplicate field"));
                    }
                }
                Ok(Unique(items.into()))
            }
        }
        d.deserialize_any(JsonVisitor)
    }
}
pub(super) fn json_bytes(data: &[u8]) -> Result<Value> {
    serde_json::from_slice::<Unique>(data)
        .map(|v| v.0)
        .map_err(|_| Error::new("invalid_request", "invalid JSON or duplicate fields"))
}
pub(super) fn kind(method: &str) -> &str {
    match method {
        "session.auth" => "AUTH",
        "ping" => "PING",
        "upload.begin" | "upload.chunk" | "upload.finish" => "SEND_GCODE",
        "upload.abort" => "ABORT_GCODE",
        "upload.receipt" => "GET_RECEIPT",
        "status.get" => "GET_STATUS",
        "status.subscribe" => "SUB_STATUS",
        "status.unsubscribe" => "UNSUB_STATUS",
        "job.start" => "START_JOB",
        "job.status" => "GET_JOB",
        "jog.start" => "JOG_START",
        "jog.keepalive" => "JOG_KEEPALIVE",
        "jog.stop" => "JOG_STOP",
        _ => "REQUEST",
    }
}
pub(super) fn encode(kind: &str, message: &Value) -> Result<Vec<u8>> {
    let body =
        serde_json::to_vec(message).map_err(|_| Error::new("invalid_message", "invalid JSON"))?;
    if body.is_empty() || body.len() > MAX_FRAME {
        return Err(Error::new("frame_too_large", "frame exceeds 65536 bytes"));
    }
    let mut bytes = vec![0; 24];
    bytes[..4].copy_from_slice(b"CAM2");
    bytes[4..4 + kind.len()].copy_from_slice(kind.as_bytes());
    bytes[20..].copy_from_slice(&(body.len() as u32).to_be_bytes());
    bytes.extend(body);
    Ok(bytes)
}
pub(super) fn header(data: &[u8]) -> Result<(&str, usize)> {
    if data.len() != 24 || &data[..4] != b"CAM2" {
        return Err(Error::new("invalid_magic", "frame must start with CAM2"));
    }
    let raw = &data[4..20];
    let end = raw.iter().position(|&b| b == 0).unwrap_or(16);
    let kind = std::str::from_utf8(&raw[..end])
        .map_err(|_| Error::new("invalid_message_type", "message type must be ASCII"))?;
    if kind.is_empty() || !kind.is_ascii() || raw[end..].iter().any(|&b| b != 0) {
        return Err(Error::new("invalid_message_type", "invalid message type"));
    }
    let size = u32::from_be_bytes(data[20..24].try_into().unwrap()) as usize;
    if !(1..=MAX_FRAME).contains(&size) {
        return Err(Error::new(
            "invalid_frame",
            "frame length must be 1 to 65536 bytes",
        ));
    }
    Ok((kind, size))
}
pub(super) fn params(value: &Value, keys: &[&str]) -> Result<()> {
    if !value
        .as_object()
        .is_some_and(|v| v.len() == keys.len() && keys.iter().all(|k| v.contains_key(*k)))
    {
        return Err(Error::new(
            "invalid_params",
            "parameters do not match this method",
        ));
    }
    Ok(())
}
pub(super) fn canonical_id(value: &str) -> bool {
    uuid::Uuid::parse_str(value).is_ok_and(|v| v.to_string() == value)
}
pub(super) struct Request {
    pub id: String,
    pub method: String,
    pub params: Value,
}
pub(super) async fn read(
    reader: &mut (impl AsyncRead + Unpin),
    idle: Duration,
    io: Duration,
) -> Result<Request> {
    let mut bytes = [0; 24];
    timeout(idle, reader.read_exact(&mut bytes)).await??;
    let (kind, size) = header(&bytes)?;
    if !matches!(
        kind,
        "AUTH"
            | "PING"
            | "SEND_GCODE"
            | "ABORT_GCODE"
            | "GET_RECEIPT"
            | "GET_STATUS"
            | "SUB_STATUS"
            | "UNSUB_STATUS"
            | "START_JOB"
            | "GET_JOB"
            | "JOG_START"
            | "JOG_KEEPALIVE"
            | "JOG_STOP"
            | "REQUEST"
            | "REPLY"
            | "ERROR"
            | "STATUS"
    ) {
        return Err(Error::new("invalid_message_type", "unknown message type"));
    }
    let mut body = vec![0; size];
    timeout(io, reader.read_exact(&mut body)).await??;
    let value = json_bytes(&body)?;
    let id = value["requestId"]
        .as_str()
        .filter(|v| (1..=64).contains(&v.chars().count()))
        .ok_or_else(|| {
            Error::new(
                "invalid_request",
                "requestId must contain 1 to 64 characters",
            )
        })?;
    let checked = || -> Result<Request> {
        if value["version"].as_u64() != Some(2) {
            return Err(Error::new(
                "unsupported_version",
                "supported CAM TCP version: 2",
            ));
        }
        if params(&value, &["version", "requestId", "method", "params"]).is_err()
            || !value["params"].is_object()
        {
            return Err(Error::new("invalid_request", "invalid request envelope"));
        }
        let method = value["method"]
            .as_str()
            .filter(|s| !s.is_empty())
            .ok_or_else(|| Error::new("invalid_request", "method must be a nonempty string"))?;
        if kind != self::kind(method) {
            return Err(Error::new(
                "message_type_mismatch",
                "header type does not match the request method",
            ));
        }
        Ok(Request {
            id: id.into(),
            method: method.into(),
            params: value["params"].clone(),
        })
    };
    checked().map_err(|mut e| {
        e.request_id = id.into();
        e
    })
}
pub(super) async fn write(
    writer: &mut (impl AsyncWrite + Unpin),
    kind: &str,
    value: &Value,
    io: Duration,
) -> Result<()> {
    timeout(io, writer.write_all(&encode(kind, value)?)).await??;
    Ok(())
}
