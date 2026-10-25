# Dedicated CNC appliance provisioning

Follow the root AGENT.md. This administrative tool owns dedicated accounts,
directories, explicit machine imports and fixed OS policy files. The public
interface is `betterlinuxcnc-appliance`. The package's fixed, byte-validated
`postinst` invokes only `provision`; it does not activate login policy.

- Require root for mutations. Passwords arrive on stdin and are never persisted in
  source, command arguments, manifests or logs. Updating software never resets them.
- Keep machine configuration in /etc/betterlinuxcnc, mutable machine data in
  /var/lib/betterlinuxcnc and application code in the package-managed /usr paths.
- `provision` is idempotent: create or validate dedicated identities and fixed
  directory ownership without changing passwords, configurations or file contents.
  Reject unexpected existing accounts, groups and symlinked directory parents.
  Keep data/cache parents root-owned; users own only their designated children.
  Reload systemd unit definitions when systemd is present, without starting services.
- `prepare` migrates copies and preserves originals; `activate` changes login
  policy only after the operator has verified the prepared installation. Neither
  command issues machine commands or kills LinuxCNC.
- `stage` and `prepare` accept the mutually exclusive explicit options
  `--zhulong-inputs-only` and `--zhulong-homing-travel-mm X Y Z`. Selectively merge
  the reviewed GPIO020/021/022 active-high, five-cycle debounce profile, preserving
  unrelated tuning and opposite limits. Reject dynamic HAL and conflicting wiring.
  Inputs-only inhibits homing. Measured travel enables only the pinned HOMEMOD;
  prepare verifies installed core/development versions, module provenance/hash and
  six ABI header hashes before account or configuration changes. Stage requires
  no local LinuxCNC installation and records that verification is still pending.
  The explicit `--zhulong-xyz-only` option additionally removes only the complete
  reviewed inactive ABC configuration and wiring, retaining XYZ tuning, spindle,
  I/O and board step-generator capacity. It requires measured homing travel.
  Retain parameter/tool files; the changed machine coordinates require an onsite
  check of work offsets after actual homing, not an automatic offset rewrite.
- `activate` enables only the low-privilege Mesa check timer when systemd is
  running, after installing policy. Provision/postinst do not start the timer;
  no activation path enables the independent root flash service.
- SSH maintenance has a fixed read-only command vocabulary. No shell, arbitrary
  paths, forwarding, file upload or generic privilege elevation.
- `backup` accepts no paths: snapshot fixed configuration, machine state and host
  policies into root-only recovery/snapshots. Verify hashes and persist the whole
  snapshot before atomic publication; retain the current and two latest older
  verified snapshots. Never prune legacy, foreign or damaged recovery entries.
- All builds and source tests run only in GitHub CI, never locally or on the target.
  Unit tests use temporary roots and subprocess CLI checks. The isolated Debian
  package CI additionally performs first/repeated installation and explicit policy
  activation, checking actual sshd/visudo output without starting SSH, a display
  manager, LinuxCNC or hardware. Target machines only install CI-built packages.
