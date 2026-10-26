//! Only the fixed 7I92 user flash area is writable; never reload, reset or recover.
use crate::Result;
use std::path::Path;
use std::process::{Command, Output};

const MESAFLASH: &str = "/usr/bin/mesaflash";
const ADDRESS: &str = "10.10.10.10";
const DEVICE: &str = "7I92";
const PART: &str = "6slx9tqg144";

pub(crate) fn write_and_verify(
    firmware: &Path,
    authorize: impl FnMut(&str) -> Result<()>,
    record: impl FnMut(&str, &[u8]) -> Result<()>,
) -> Result<()> {
    crate::platform::trusted_file(Path::new(MESAFLASH), false)?;
    run(firmware, authorize, record, |command| Ok(command.output()?))
}

fn run(
    firmware: &Path,
    mut authorize: impl FnMut(&str) -> Result<()>,
    mut record: impl FnMut(&str, &[u8]) -> Result<()>,
    mut execute: impl FnMut(&mut Command) -> Result<Output>,
) -> Result<()> {
    for (step, argument) in [
        ("probe", "--verbose"),
        ("write", "--write"),
        ("verify", "--verify"),
    ] {
        authorize(step)?;
        let mut command = crate::platform::command(MESAFLASH);
        command.args(["--device", DEVICE, "--addr", ADDRESS, argument]);
        if step != "probe" {
            command.arg(firmware);
        }
        let output = execute(&mut command)?;
        let mut log = output.stdout.clone();
        log.extend_from_slice(&output.stderr);
        if log.len() > 1024 * 1024 {
            return Err("Mesa hardware response exceeds limit; control remains stopped".into());
        }
        record(step, &log)?;
        if !output.status.success() {
            return Err(format!("Mesa {step} failed; control remains stopped").into());
        }
        let text = std::str::from_utf8(&output.stdout)?;
        if step == "probe" {
            identity(text)?;
        } else {
            let required = if step == "write" {
                "Board configuration updated successfully."
            } else {
                "Board configuration verified successfully."
            };
            if !text.lines().any(|line| line.trim() == required) {
                return Err(format!(
                    "Mesa {step} did not confirm completion; control remains stopped"
                )
                .into());
            }
        }
    }
    authorize("complete")?;
    Ok(())
}

fn identity(text: &str) -> Result<()> {
    let devices: Vec<_> = text
        .lines()
        .map(str::trim)
        .filter(|line| line.starts_with("ETH device "))
        .collect();
    let parts: Vec<_> = text
        .lines()
        .map(str::trim)
        .filter_map(|line| line.strip_prefix("FPGA type: "))
        .collect();
    if devices != [format!("ETH device {DEVICE} at ip={ADDRESS}")]
        || parts != [PART]
        || text
            .lines()
            .filter(|line| line.trim() == "Connectors count: 2")
            .count()
            != 1
        || text
            .lines()
            .filter(|line| line.trim() == "Pins per connector: 17")
            .count()
            != 1
    {
        return Err("The fixed Ethernet target is not the approved 7I92/6slx9tqg144 board".into());
    }
    Ok(())
}

pub(crate) fn validate_bit(bytes: &[u8]) -> Result<()> {
    let mut reader = BitReader(bytes);
    let preamble = reader.short_field()?;
    if preamble != [0x0f, 0xf0, 0x0f, 0xf0, 0x0f, 0xf0, 0x0f, 0xf0, 0x00]
        || reader.take(2)? != [0, 1]
    {
        return Err("Firmware is not a supported Xilinx bitstream".into());
    }
    for tag in b"abcd" {
        if reader.take(1)? != [*tag] {
            return Err("Malformed Xilinx bitstream header".into());
        }
        let value = reader.short_field()?;
        if value.is_empty() || value.last() != Some(&0) || value.len() > 4096 {
            return Err("Invalid Xilinx bitstream header field".into());
        }
        if *tag == b'b' && value != b"6slx9tqg144\0" {
            return Err("Firmware FPGA part differs from the approved board".into());
        }
    }
    if reader.take(1)? != b"e" {
        return Err("Xilinx bitstream payload is missing".into());
    }
    let length = u32::from_be_bytes(reader.take(4)?.try_into()?) as usize;
    if length == 0 || length != reader.0.len() {
        return Err("Xilinx bitstream payload length is inconsistent".into());
    }
    Ok(())
}

struct BitReader<'a>(&'a [u8]);

impl<'a> BitReader<'a> {
    fn take(&mut self, length: usize) -> Result<&'a [u8]> {
        if self.0.len() < length {
            return Err("Truncated Xilinx bitstream".into());
        }
        let (value, rest) = self.0.split_at(length);
        self.0 = rest;
        Ok(value)
    }
    fn short_field(&mut self) -> Result<&'a [u8]> {
        let length = u16::from_be_bytes(self.take(2)?.try_into()?) as usize;
        self.take(length)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt;
    use std::os::unix::process::ExitStatusExt;

    const IDENTITY: &str = "ETH device 7I92 at ip=10.10.10.10\nBoard info:\n  Connectors count: 2\n  Pins per connector: 17\n  FPGA type: 6slx9tqg144\n";

    #[test]
    fn fixed_commands_require_identity_write_and_explicit_readback_in_order() {
        for failed_step in [None, Some("probe"), Some("write"), Some("verify")] {
            let mut calls = Vec::new();
            let result =
                run(
                    Path::new("/var/cache/betterlinuxcnc/mesa-flash/firmware.bit"),
                    |_| Ok(()),
                    |_, _| Ok(()),
                    |command| {
                        assert_eq!(command.get_program(), MESAFLASH);
                        let args: Vec<_> = command
                            .get_args()
                            .map(|value| value.to_str().unwrap())
                            .collect();
                        assert_eq!(&args[..4], ["--device", "7I92", "--addr", "10.10.10.10"]);
                        assert!(args.iter().all(|arg| ![
                            "--reload",
                            "--reset",
                            "--fallback",
                            "--fix-boot-block",
                            "--program",
                            "--no-auto-verify"
                        ]
                        .contains(arg)));
                        let step = match args[4] {
                            "--verbose" => "probe",
                            "--write" => "write",
                            "--verify" => "verify",
                            _ => panic!("unexpected command"),
                        };
                        calls.push(step);
                        Ok(Output {
                            status: std::process::ExitStatus::from_raw(
                                if failed_step == Some(step) { 256 } else { 0 },
                            ),
                            stdout: match step {
                                "probe" => IDENTITY,
                                "write" => "Board configuration updated successfully.\n",
                                _ => "Board configuration verified successfully.\n",
                            }
                            .as_bytes()
                            .to_vec(),
                            stderr: Vec::new(),
                        })
                    },
                );
            assert_eq!(result.is_ok(), failed_step.is_none());
            assert_eq!(
                calls.len(),
                match failed_step {
                    Some("probe") => 1,
                    Some("write") => 2,
                    _ => 3,
                }
            );
        }
        for altered in [
            IDENTITY.replace("7I92", "7I92T"),
            IDENTITY.replace("10.10.10.10", "10.10.10.11"),
            IDENTITY.replace("6slx9tqg144", "6slx16ftg256"),
            format!("{IDENTITY}{IDENTITY}"),
        ] {
            assert!(identity(&altered).is_err());
        }
    }

    #[test]
    fn actual_process_failure_cannot_become_a_successful_readback() {
        let directory = tempfile::tempdir().unwrap();
        let fixture = directory.path().join("mesaflash-fixture");
        std::fs::write(&fixture, format!("#!/bin/sh\ncase \"$5\" in\n--verbose) printf '{IDENTITY}' ;;\n--write) echo 'Board configuration updated successfully.' ;;\n--verify) echo 'Board configuration verified successfully.'; exit 1 ;;\nesac\n")).unwrap();
        std::fs::set_permissions(&fixture, std::fs::Permissions::from_mode(0o700)).unwrap();
        let mut calls = 0;
        let result = run(
            Path::new("/unused/verified.bit"),
            |_| Ok(()),
            |_, _| Ok(()),
            |expected| {
                calls += 1;
                let mut process = Command::new(&fixture);
                process.env_clear().args(expected.get_args());
                Ok(process.output()?)
            },
        );
        assert!(result.is_err());
        assert_eq!(calls, 3);
    }

    #[test]
    fn bitstream_part_and_lengths_are_checked_before_hardware_access() {
        let mut bytes = vec![
            0, 9, 0x0f, 0xf0, 0x0f, 0xf0, 0x0f, 0xf0, 0x0f, 0xf0, 0, 0, 1,
        ];
        for (tag, value) in [
            (b'a', "TopEthernetHostMot2.ncd\0"),
            (b'b', "6slx9tqg144\0"),
            (b'c', "2026/10/26\0"),
            (b'd', "12:00:00\0"),
        ] {
            bytes.push(tag);
            bytes.extend_from_slice(&(value.len() as u16).to_be_bytes());
            bytes.extend_from_slice(value.as_bytes());
        }
        bytes.extend_from_slice(b"e\x00\x00\x00\x03bit");
        validate_bit(&bytes).unwrap();
        assert!(validate_bit(&bytes[..bytes.len() - 1]).is_err());
        let position = bytes
            .windows(b"6slx9tqg144\0".len())
            .position(|window| window == b"6slx9tqg144\0")
            .unwrap();
        bytes[position + 4] = b'8';
        assert!(validate_bit(&bytes).is_err());
    }
}
