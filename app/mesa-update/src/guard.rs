//! FD protocol shared through processes, not through another crate's internals.
use crate::Result;
use serde::Deserialize;
use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::os::fd::{AsRawFd, FromRawFd};
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
use std::os::unix::net::UnixStream;
use std::path::Path;
use std::time::Duration;

const PROTOCOL: &str = "betterlinuxcnc-mesa-maintenance-v1";
const UPDATER: &str = "/usr/bin/betterlinuxcnc-updater";
const LOCK: &str = "/var/cache/betterlinuxcnc/update/update.lock";

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    protocol: String,
    challenge: String,
    version: String,
}

pub(crate) struct Guard {
    stream: UnixStream,
    _lock: File,
    challenge: String,
    version: String,
    step: usize,
}

impl Guard {
    pub(crate) fn inherited() -> Result<Self> {
        crate::platform::require_root()?;
        if !cfg!(target_os = "linux") {
            return Err("Mesa guarded writes require Linux process credentials".into());
        }
        // F_DUPFD rejects absent descriptors before constructing owned handles.
        let stream = unsafe { UnixStream::from_raw_fd(copy_descriptor(3)?) };
        let lock = unsafe { File::from_raw_fd(copy_descriptor(4)?) };
        validate_peer(&stream)?;
        validate_lock(&lock)?;
        // Retain only our CLOEXEC duplicates. Hardware commands must never inherit
        // the authorization channel or keep the controller's maintenance lock.
        unsafe {
            libc::close(3);
            libc::close(4);
        }
        Self::handshake(stream, lock)
    }

    fn handshake(mut stream: UnixStream, lock: File) -> Result<Self> {
        stream.set_read_timeout(Some(Duration::from_secs(10)))?;
        stream.set_write_timeout(Some(Duration::from_secs(10)))?;
        let request: Request = serde_json::from_str(&read_line(&mut stream)?)?;
        if request.protocol != PROTOCOL
            || uuid::Uuid::parse_str(&request.challenge).is_err()
            || !crate::contract::valid_version(&request.version)
        {
            return Err("Invalid Mesa maintenance capability".into());
        }
        writeln!(stream, "ready {}", request.challenge)?;
        Ok(Self {
            stream,
            _lock: lock,
            challenge: request.challenge,
            version: request.version,
            step: 0,
        })
    }

    pub(crate) fn version(&self) -> &str {
        &self.version
    }

    pub(crate) fn authorize(&mut self, step: &str) -> Result<()> {
        let expected = ["probe", "write", "verify", "complete"]
            .get(self.step)
            .copied();
        if expected != Some(step) {
            return Err("Mesa hardware operation is out of order".into());
        }
        writeln!(self.stream, "{step} {}", self.challenge)?;
        if read_line(&mut self.stream)? != format!("continue {}", self.challenge) {
            return Err(
                "The live maintenance guard did not authorize this hardware operation".into(),
            );
        }
        self.step += 1;
        Ok(())
    }
}

fn copy_descriptor(fd: i32) -> Result<i32> {
    let copy = unsafe { libc::fcntl(fd, libc::F_DUPFD_CLOEXEC, 10) };
    if copy < 0 {
        return Err("Mesa write requires inherited maintenance descriptors".into());
    }
    Ok(copy)
}

#[cfg(target_os = "linux")]
fn validate_peer(stream: &UnixStream) -> Result<()> {
    let mut credential = libc::ucred {
        pid: 0,
        uid: u32::MAX,
        gid: u32::MAX,
    };
    let mut size = std::mem::size_of::<libc::ucred>() as libc::socklen_t;
    if unsafe {
        libc::getsockopt(
            stream.as_raw_fd(),
            libc::SOL_SOCKET,
            libc::SO_PEERCRED,
            (&mut credential as *mut libc::ucred).cast(),
            &mut size,
        )
    } != 0
        || size as usize != std::mem::size_of::<libc::ucred>()
        || credential.uid != 0
        || credential.pid != unsafe { libc::getppid() }
    {
        return Err("Mesa maintenance peer is not the direct root parent".into());
    }
    let parent = std::fs::read_link(format!("/proc/{}/exe", credential.pid))?;
    if parent != Path::new(UPDATER) {
        return Err("Mesa maintenance parent is not the installed updater".into());
    }
    crate::platform::trusted_file(Path::new(UPDATER), false)?;
    Ok(())
}

#[cfg(not(target_os = "linux"))]
fn validate_peer(_: &UnixStream) -> Result<()> {
    Err("Mesa writes require Linux peer credentials".into())
}

fn validate_lock(inherited: &File) -> Result<()> {
    let expected = crate::platform::trusted_file(Path::new(LOCK), true)?;
    let received = inherited.metadata()?;
    let info = expected.metadata()?;
    if received.dev() != info.dev() || received.ino() != info.ino() {
        return Err("Mesa maintenance inherited the wrong operation lock".into());
    }
    // A separate open description must conflict with the parent's inherited lock.
    // This does not acquire/release the inherited description's own flock.
    let competing = OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW)
        .open(LOCK)?;
    if unsafe { libc::flock(competing.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } == 0 {
        return Err("Mesa maintenance lock is not held by the parent".into());
    }
    if std::io::Error::last_os_error().raw_os_error() != Some(libc::EWOULDBLOCK) {
        return Err("Cannot establish the Mesa maintenance lock state".into());
    }
    Ok(())
}

fn read_line(stream: &mut UnixStream) -> Result<String> {
    let mut bytes = Vec::new();
    for _ in 0..512 {
        let mut byte = [0];
        stream.read_exact(&mut byte)?;
        if byte[0] == b'\n' {
            return Ok(String::from_utf8(bytes)?);
        }
        bytes.push(byte[0]);
    }
    Err("Mesa maintenance capability exceeds limit".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_unrelated_socket_is_not_a_root_updater_capability() {
        let (socket, _peer) = UnixStream::pair().unwrap();
        assert!(validate_peer(&socket).is_err());
    }

    #[test]
    fn capability_is_challenged_and_each_step_needs_the_live_peer() {
        let (mut parent, child) = UnixStream::pair().unwrap();
        let worker = std::thread::spawn(move || {
            let request = serde_json::json!({"protocol":PROTOCOL,"challenge":"c31cb822-4e86-46bf-a8cc-d35d260d8abb","version":"26.10.26.1"});
            writeln!(parent, "{request}").unwrap();
            assert_eq!(
                read_line(&mut parent).unwrap(),
                "ready c31cb822-4e86-46bf-a8cc-d35d260d8abb"
            );
            assert_eq!(
                read_line(&mut parent).unwrap(),
                "probe c31cb822-4e86-46bf-a8cc-d35d260d8abb"
            );
            writeln!(parent, "continue c31cb822-4e86-46bf-a8cc-d35d260d8abb").unwrap();
            // Loss of the root guard must reject the subsequent write.
        });
        let mut guard = Guard::handshake(child, tempfile::tempfile().unwrap()).unwrap();
        assert_eq!(guard.version(), "26.10.26.1");
        assert!(guard.authorize("write").is_err());
        guard.authorize("probe").unwrap();
        worker.join().unwrap();
        assert!(guard.authorize("write").is_err());
    }
}
