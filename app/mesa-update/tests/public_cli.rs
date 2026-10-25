use std::process::Command;

#[test]
fn both_processes_have_independent_fixed_command_interfaces() {
    for binary in [
        env!("CARGO_BIN_EXE_betterlinuxcnc-mesa-update"),
        env!("CARGO_BIN_EXE_betterlinuxcnc-mesa-flash"),
    ] {
        let output = Command::new(binary).arg("--help").output().unwrap();
        assert!(output.status.success());
        assert!(!output.stdout.is_empty());
        for args in [
            ["--package", "/tmp/firmware.bit"],
            ["--url", "https://example.com/firmware.bit"],
            ["--address", "192.168.1.1"],
        ] {
            let output = Command::new(binary).args(args).output().unwrap();
            assert!(!output.status.success());
        }
    }
    let output = Command::new(env!("CARGO_BIN_EXE_betterlinuxcnc-mesa-update"))
        .arg("apply-system")
        .output()
        .unwrap();
    assert!(!output.status.success());
    let output = Command::new(env!("CARGO_BIN_EXE_betterlinuxcnc-mesa-flash"))
        .args(["apply-system", "/tmp/user.bit"])
        .output()
        .unwrap();
    assert!(!output.status.success());
}
