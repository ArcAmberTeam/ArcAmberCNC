use super::protocol::{canonical_id, json_bytes, Error, Result};
use base64::{engine::general_purpose::STANDARD, Engine};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, DirBuilder, File, OpenOptions},
    io::Write,
    os::unix::fs::{DirBuilderExt, MetadataExt, OpenOptionsExt, PermissionsExt},
    path::{Path, PathBuf},
    sync::{Arc, Mutex},
};
use tempfile::TempDir;

#[derive(Clone)]
pub(super) struct Inbox {
    pub directory: PathBuf,
    max_bytes: u64,
    publication: Arc<Mutex<()>>,
}
pub(super) struct Upload {
    directory: TempDir,
    stream: File,
    data: Value,
    hash: Sha256,
    tail: Vec<u8>,
    pub offset: u64,
}
fn error(code: &str, message: &str) -> Error {
    Error::new(code, message)
}
fn id(value: &Value) -> Result<&str> {
    value
        .as_str()
        .filter(|s| canonical_id(s))
        .ok_or_else(|| error("invalid_transfer_id", "transferId must be a lowercase UUID"))
}
fn private_file(path: &Path) -> std::io::Result<File> {
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(path)
}
fn sync(path: &Path) -> std::io::Result<()> {
    File::open(path)?.sync_all()
}
impl Inbox {
    pub fn new(path: &Path, max_bytes: u64) -> Result<Self> {
        DirBuilder::new().recursive(true).mode(0o700).create(path)?;
        let meta = fs::symlink_metadata(path)?;
        if !meta.is_dir() || meta.uid() != unsafe { libc::getuid() } || meta.mode() & 0o077 != 0 {
            return Err(error(
                "configuration",
                "inbox must be a user-owned directory with mode 0700",
            ));
        }
        Ok(Self {
            directory: path.canonicalize()?,
            max_bytes,
            publication: Arc::new(Mutex::new(())),
        })
    }
    pub fn begin(&self, data: &Value) -> Result<Upload> {
        id(&data["transferId"])?;
        let valid = data["filename"].as_str().is_some_and(|name| {
            let Some((stem, ext)) = name.rsplit_once('.') else {
                return false;
            };
            (1..=120).contains(&stem.len())
                && stem.as_bytes()[0].is_ascii_alphanumeric()
                && stem
                    .bytes()
                    .all(|c| c.is_ascii_alphanumeric() || b"_.-".contains(&c))
                && matches!(ext, "ngc" | "nc" | "gcode")
        });
        if !valid {
            return Err(error(
                "invalid_filename",
                "filename must be a plain .ngc, .nc or .gcode name",
            ));
        }
        if !data["size"]
            .as_u64()
            .is_some_and(|v| v > 0 && v <= self.max_bytes)
        {
            return Err(error(
                "invalid_size",
                "program size must be positive and within the limit",
            ));
        }
        if !data["sha256"].as_str().is_some_and(|s| {
            s.len() == 64
                && s.bytes()
                    .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
        }) {
            return Err(error(
                "invalid_sha256",
                "sha256 must contain 64 lowercase hex digits",
            ));
        }
        let directory = tempfile::Builder::new()
            .prefix(".receiving-")
            .permissions(fs::Permissions::from_mode(0o700))
            .tempdir_in(&self.directory)?;
        let stream = private_file(&directory.path().join(data["filename"].as_str().unwrap()))?;
        let mut data = data.clone();
        data["state"] = "received".into();
        Ok(Upload {
            directory,
            stream,
            data,
            hash: Sha256::new(),
            tail: Vec::new(),
            offset: 0,
        })
    }
    pub fn receipt(&self, transfer_id: &Value) -> Result<Value> {
        let directory = self.directory.join(id(transfer_id)?);
        let path = directory.join("receipt.json");
        for p in [&directory, &path] {
            match fs::symlink_metadata(p) {
                Ok(meta) if !meta.file_type().is_symlink() => {}
                Ok(_) => return Err(error("invalid_receipt", "receipt paths cannot be symlinks")),
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                    return Err(error(
                        "unknown_transfer",
                        "no complete program has this transferId",
                    ))
                }
                Err(e) => return Err(e.into()),
            }
        }
        let bytes = fs::read(path)?;
        let data = json_bytes(&bytes)
            .map_err(|_| error("invalid_receipt", "stored receipt is not valid JSON"))?;
        if !data.is_object() || data["transferId"] != *transfer_id {
            return Err(error(
                "invalid_receipt",
                "stored receipt has an invalid identity",
            ));
        }
        Ok(data)
    }
    pub fn identify(&self, file: &Value) -> Option<Value> {
        let path = Path::new(file.as_str()?).canonicalize().ok()?;
        let parent = path.parent()?;
        if parent.parent() != Some(self.directory.as_path()) {
            return None;
        }
        let id = Value::from(parent.file_name()?.to_str()?);
        let receipt = self.receipt(&id).ok()?;
        (path.file_name()?.to_str()? == receipt["filename"].as_str()?).then_some(id)
    }
    pub fn finish(&self, mut upload: Upload) -> Result<Value> {
        if upload.offset != upload.data["size"].as_u64().unwrap() {
            return Err(error(
                "incomplete_program",
                "received size differs from declared size",
            ));
        }
        if !upload.tail.is_empty() {
            return Err(error(
                "invalid_program",
                "program ends inside a UTF-8 character",
            ));
        }
        if format!("{:x}", upload.hash.finalize()) != upload.data["sha256"].as_str().unwrap() {
            return Err(error("sha256_mismatch", "SHA-256 mismatch"));
        }
        upload.stream.flush()?;
        upload.stream.sync_all()?;
        let mut receipt = private_file(&upload.directory.path().join("receipt.json"))?;
        receipt.write_all(&serde_json::to_vec(&upload.data).unwrap())?;
        receipt.sync_all()?;
        sync(upload.directory.path())?;
        // All sessions publish under the same lock; existing IDs are immutable.
        let _guard = self.publication.lock().unwrap();
        let target = self
            .directory
            .join(upload.data["transferId"].as_str().unwrap());
        let duplicate = fs::symlink_metadata(&target).is_ok();
        if duplicate {
            if self.receipt(&upload.data["transferId"])? != upload.data {
                return Err(error(
                    "transfer_id_conflict",
                    "transferId already has different content",
                ));
            }
        } else {
            fs::rename(upload.directory.path(), target)?;
            sync(&self.directory)?;
        }
        upload.data["duplicate"] = duplicate.into();
        Ok(upload.data)
    }
}
impl Upload {
    pub fn write(&mut self, params: &Value) -> Result<Value> {
        if params["offset"].as_u64() != Some(self.offset) {
            return Err(error(
                "offset_mismatch",
                "chunk offset must match nextOffset",
            ));
        }
        let data = params["data"]
            .as_str()
            .filter(|s| !s.is_empty() && s.len() <= 43692)
            .ok_or_else(|| {
                error(
                    "invalid_chunk",
                    "chunk must contain 1 to 32768 decoded bytes",
                )
            })?;
        let chunk = STANDARD
            .decode(data)
            .map_err(|_| error("invalid_chunk", "chunk data must be Base64"))?;
        if chunk.is_empty() || chunk.len() > 32768 {
            return Err(error(
                "invalid_chunk",
                "chunk must contain 1 to 32768 decoded bytes",
            ));
        }
        if self.offset + chunk.len() as u64 > self.data["size"].as_u64().unwrap() {
            return Err(error(
                "invalid_chunk_size",
                "chunk exceeds the declared program size",
            ));
        }
        if chunk.contains(&0) {
            return Err(error(
                "invalid_program",
                "program must not contain NUL bytes",
            ));
        }
        self.tail.extend_from_slice(&chunk);
        match std::str::from_utf8(&self.tail) {
            Ok(_) => self.tail.clear(),
            Err(e) if e.error_len().is_none() => {
                self.tail.drain(..e.valid_up_to());
            }
            Err(_) => return Err(error("invalid_program", "program must be UTF-8")),
        }
        self.stream.write_all(&chunk)?;
        self.hash.update(&chunk);
        self.offset += chunk.len() as u64;
        Ok(json!({"nextOffset":self.offset}))
    }
}
