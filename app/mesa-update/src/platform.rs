use crate::contract::valid_version;
use crate::Result;
use std::process::Command;

pub(crate) fn operating_user() -> Result<u32> {
    let name = c"linuxcnc";
    // This process is single-threaded at entry; copy the uid before any network work.
    let entry = unsafe { libc::getpwnam(name.as_ptr()) };
    if entry.is_null() {
        return Err("The fixed linuxcnc operating account has not been provisioned".into());
    }
    let uid = unsafe { (*entry).pw_uid };
    if uid == 0 {
        return Err("The linuxcnc operating account must not be root".into());
    }
    Ok(uid)
}

pub(crate) fn require_operator() -> Result<u32> {
    let uid = operating_user()?;
    if unsafe { libc::geteuid() } != uid || unsafe { libc::getuid() } != uid {
        return Err("Mesa checks and downloads must run as the fixed linuxcnc account".into());
    }
    Ok(uid)
}

pub(crate) fn require_root() -> Result<()> {
    if unsafe { libc::geteuid() } != 0 || unsafe { libc::getuid() } != 0 {
        return Err("The separate Mesa flash entry requires the root system service".into());
    }
    Ok(())
}

pub(crate) fn installed_version() -> Result<String> {
    let output = Command::new("/usr/bin/dpkg-query")
        .env_clear()
        .env("PATH", "/usr/sbin:/usr/bin:/sbin:/bin")
        .env("HOME", "/")
        .env("LANG", "C")
        .current_dir("/")
        .args([
            "-W",
            "-f=${db:Status-Status}\n${Version}\n",
            "betterlinuxcnc-qt",
        ])
        .output()
        .map_err(|_| "Cannot query the installed application package")?;
    if !output.status.success() {
        return Err("The application package is not installed".into());
    }
    parse_installed_version(&output.stdout)
}

fn parse_installed_version(bytes: &[u8]) -> Result<String> {
    let text = std::str::from_utf8(bytes)?;
    let lines: Vec<_> = text.lines().collect();
    if lines.len() != 2 || lines[0] != "installed" || !valid_version(lines[1]) {
        return Err(
            "The application package must be completely installed at a supported release version"
                .into(),
        );
    }
    Ok(lines[1].to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn partial_install_and_untrusted_version_text_are_rejected() {
        assert_eq!(
            parse_installed_version(b"installed\n26.10.26.1\n").unwrap(),
            "26.10.26.1"
        );
        for bytes in [
            b"unpacked\n26.10.26.1\n".as_slice(),
            b"half-configured\n26.10.26.1\n",
            b"installed\n../../main\n",
            b"installed\n26.10.26.1\nextra\n",
        ] {
            assert!(parse_installed_version(bytes).is_err());
        }
    }
}
