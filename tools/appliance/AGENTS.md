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
