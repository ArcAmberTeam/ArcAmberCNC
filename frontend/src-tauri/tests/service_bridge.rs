use betterlinuxcnc_desktop::probe_service;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::UnixListener;

struct Process(Child);

impl Drop for Process {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

fn start_python(socket: &Path) -> Process {
    let source = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../backend/src");
    let python = std::env::var("SERVICE_TEST_PYTHON").unwrap_or_else(|_| "python3".into());
    let mut process = Process(
        Command::new(python)
            .env("PYTHONPATH", source)
            .args(["-m", "betterlinuxcnc_service", "--socket"])
            .arg(socket)
            .stdout(Stdio::null())
            .spawn()
            .expect("start Python 3.11+ service"),
    );
    let deadline = Instant::now() + Duration::from_secs(5);
    while !socket.exists() {
        assert!(process.0.try_wait().unwrap().is_none(), "service exited");
        assert!(Instant::now() < deadline, "service startup timed out");
        std::thread::sleep(Duration::from_millis(10));
    }
    process
}

#[tokio::test]
async fn probes_real_python_service_without_claiming_machine_connection() {
    let directory = tempfile::tempdir_in("/tmp").unwrap();
    let socket = directory.path().join("private/control.sock");
    let _process = start_python(&socket);
    let health = probe_service(&socket).await.unwrap();
    assert_eq!(health.service, "betterlinuxcnc");
    assert_eq!(health.mode, "diagnostics-only");
    assert!(!health.machine_connected);
}

#[tokio::test]
async fn rejects_wrong_versions_and_false_machine_feedback() {
    for (version, connected) in [(2, false), (1, true)] {
        let directory = tempfile::tempdir_in("/tmp").unwrap();
        let path = directory.path().join("control.sock");
        let listener = UnixListener::bind(&path).unwrap();
        let server = tokio::spawn(async move {
            let (mut stream, _) = listener.accept().await.unwrap();
            let size = stream.read_u32().await.unwrap();
            let mut request = vec![0; size as usize];
            stream.read_exact(&mut request).await.unwrap();
            let reply = serde_json::to_vec(&serde_json::json!({
                "version": version,
                "request_id": "desktop-health",
                "result": {"service":"betterlinuxcnc", "mode":"diagnostics-only", "machine_connected":connected}
            })).unwrap();
            stream.write_u32(reply.len() as u32).await.unwrap();
            stream.write_all(&reply).await.unwrap();
        });
        assert!(probe_service(&path).await.is_err());
        server.await.unwrap();
    }
}

#[tokio::test]
async fn missing_service_is_an_error_not_a_fake_connection() {
    let directory = tempfile::tempdir_in("/tmp").unwrap();
    assert!(probe_service(&directory.path().join("missing.sock"))
        .await
        .is_err());
}
