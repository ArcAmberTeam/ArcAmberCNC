use std::{env, path::PathBuf, process::Command};

#[test]
fn public_cam_and_controller_contracts() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .unwrap()
        .to_owned();
    let python = env::var_os("SERVICE_TEST_PYTHON").unwrap_or_else(|| "python3".into());
    let paths = env::join_paths([
        root.join("app/controller/src"),
        root.join("app/controller/tests"),
    ])
    .unwrap();
    let output = Command::new(python)
        .args(["-m", "unittest", "discover", "-s", "tests/python", "-v"])
        .current_dir(root.join("app/cam-link"))
        .env(
            "CAM_LINK_BINARY",
            env!("CARGO_BIN_EXE_betterlinuxcnc-cam-link"),
        )
        .env("PYTHONPATH", paths)
        .output()
        .expect("Python 3.11+ is required for public service contract tests");
    assert!(
        output.status.success(),
        "{}\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
}
