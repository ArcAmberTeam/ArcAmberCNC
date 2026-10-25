use crate::Result;
use serde::{Deserialize, Serialize};

pub(crate) const BOARD: &str = "zhulong-v2";
pub(crate) const VARIANT: &str = "PIN_ZHULONG_V2_34";
pub(crate) const MAX_BIT_BYTES: u64 = 16 * 1024 * 1024;

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Manifest {
    pub schema_version: u32,
    pub version: String,
    pub tag_name: String,
    pub board: String,
    pub variant: String,
    pub fpga: String,
    pub package: String,
    pub physical_constraints_verified: bool,
    pub source_commit: String,
    pub compatible_app_version: String,
    pub firmware: Firmware,
    pub artifacts: Artifacts,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Firmware {
    pub available: bool,
    pub asset: Option<String>,
    pub sha256: Option<String>,
    pub size: Option<u64>,
    pub origin: String,
    pub verification: Verification,
    pub reason: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Verification {
    pub implementation: bool,
    pub timing: bool,
    pub board_approved: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Artifacts {
    pub source: Artifact,
    pub integration: Artifact,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Artifact {
    pub asset: String,
    pub sha256: String,
    pub size_bytes: u64,
}

impl Manifest {
    pub(crate) fn validate(&self, expected_version: &str) -> Result<()> {
        if self.schema_version != 1
            || !valid_version(&self.version)
            || self.version != expected_version
            || self.tag_name != format!("v{}", self.version)
            || self.compatible_app_version != self.version
            || self.board != BOARD
            || self.variant != VARIANT
            || self.fpga != "xc6slx9"
            || self.package != "tqg144"
            || !valid_hex(&self.source_commit, 40)
        {
            return Err("Mesa release identity or application version does not match".into());
        }
        for artifact in [&self.artifacts.source, &self.artifacts.integration] {
            if !valid_asset(&artifact.asset)
                || !valid_hex(&artifact.sha256, 64)
                || artifact.size_bytes == 0
                || artifact.size_bytes > 1024 * 1024 * 1024
            {
                return Err("Invalid Mesa source/integration artifact metadata".into());
            }
        }
        let firmware = &self.firmware;
        let verified = &firmware.verification;
        if firmware.reason.len() > 4096 {
            return Err("Mesa firmware reason exceeds limit".into());
        }
        if !firmware.available {
            if firmware.asset.is_some()
                || firmware.sha256.is_some()
                || firmware.size.is_some()
                || firmware.origin != "unavailable"
                || verified.implementation
                || verified.timing
                || verified.board_approved
            {
                return Err("Unavailable firmware must not advertise a usable bitstream".into());
            }
            return Ok(());
        }
        if !self.physical_constraints_verified
            || firmware.origin != "ci-build"
            || !verified.implementation
            || !verified.timing
            || !verified.board_approved
            || !firmware
                .asset
                .as_deref()
                .is_some_and(|name| valid_asset(name) && name.ends_with(".bit"))
            || !firmware
                .sha256
                .as_deref()
                .is_some_and(|hash| valid_hex(hash, 64))
            || !firmware
                .size
                .is_some_and(|size| size > 0 && size <= MAX_BIT_BYTES)
        {
            return Err(
                "Firmware lacks verified CI, timing, board or physical-constraint evidence".into(),
            );
        }
        Ok(())
    }
}

pub(crate) fn valid_version(version: &str) -> bool {
    !version.is_empty()
        && version.len() <= 64
        && version.split('.').count() >= 2
        && version
            .split('.')
            .all(|part| !part.is_empty() && part.bytes().all(|byte| byte.is_ascii_digit()))
}

pub(crate) fn valid_asset(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 160
        && name.as_bytes()[0].is_ascii_alphanumeric()
        && !name.contains("..")
        && name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-' | b'_'))
}

fn valid_hex(value: &str, length: usize) -> bool {
    value.len() == length
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

#[cfg(test)]
pub(crate) fn fixture() -> Manifest {
    serde_json::from_str(include_str!("../tests/fixtures/mesa-release.json")).unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn source_only_release_is_valid_but_has_no_firmware() {
        let manifest = fixture();
        manifest.validate("26.10.26.1").unwrap();
        assert!(!manifest.firmware.available);
        assert!(manifest.validate("26.10.27.1").is_err());
    }

    #[test]
    fn original_or_unverified_bits_cannot_be_advertised_as_ready() {
        let mut manifest = fixture();
        manifest.firmware.available = true;
        manifest.firmware.asset = Some("zhulong-v2-26.10.26.1.bit".into());
        manifest.firmware.sha256 = Some("a".repeat(64));
        manifest.firmware.size = Some(340884);
        manifest.firmware.origin = "vendor-original".into();
        assert!(manifest.validate("26.10.26.1").is_err());
        manifest.firmware.origin = "ci-build".into();
        assert!(manifest.validate("26.10.26.1").is_err());
        manifest.firmware.verification = Verification {
            implementation: true,
            timing: true,
            board_approved: true,
        };
        assert!(manifest.validate("26.10.26.1").is_err());
        manifest.physical_constraints_verified = true;
        manifest.validate("26.10.26.1").unwrap();
        manifest.firmware.asset = Some("../old.bit".into());
        assert!(manifest.validate("26.10.26.1").is_err());
    }

    #[test]
    fn false_metadata_cannot_hide_a_download_or_verification_claim() {
        let mut manifest = fixture();
        manifest.firmware.asset = Some("old.bit".into());
        assert!(manifest.validate("26.10.26.1").is_err());
        manifest.firmware.asset = None;
        manifest.firmware.verification.board_approved = true;
        assert!(manifest.validate("26.10.26.1").is_err());
    }
}
