# Python startup orchestration boundaries

Follow the root [AGENT.md](../../AGENT.md). `$code-boundary-standards` is permanently disabled in this repository and is not a prerequisite for development, testing, or review.

- `main` in `bettercnc_launcher`, `python -m bettercnc_launcher`, and `betterlinuxcnc-launch` are public entry points. Underscore-prefixed files are private. Runtime dependencies are limited to the Python standard library.
- The launcher owns configuration validation, single-instance locking, child processes, logs, startup order, and readiness probes. It uses only installed CLIs and the read-only public Unix protocol; it must not import Qt, LinuxCNC, service, or controller implementation, obtain control sessions, or send machine commands.
- Native `linuxcnc <ini>` continues to own the real-time core, HAL, DISPLAY, and low-level cleanup. The launcher does not rewrite INI/HAL or take over existing services. Default supervision restarts only exited modules without replaying commands. Core restart requires confirmation that the original process group and native lock have been released.
- Installation provides XDG autostart, a dedicated X11 session, and systemd user services, without starting a root GUI. `--kiosk-session` continuously maintains the dedicated session and uses the installed desktop CLI to show a startup-status page without machine connectivity; launcher failure does not fall back to the ordinary desktop. SIGINT/SIGTERM/SIGKILL of the main process must not trigger systemd restart. Exit 78 indicates a runtime condition requiring human intervention; never use systemd loops to preempt other instances.
- Start the controller service first; enable CAM only after LinuxCNC status connects. Failures after core startup must leave the core/controller available for the local operator. Stop signals request native cleanup only when fresh state explicitly shows idle; never force-kill the core process group.
- Tests observe public CLI, real processes, and Unix sockets using executable substitutes, without LinuxCNC, simulators, real-time threads, or hardware. Test installed wheels and verify dependency boundaries and desktop install entry points. The user currently prohibits local/target builds and source tests, including local Docker; only GitHub CI performs these checks. The target installs completed DEBs only. All Markdown follows the protection rules below.

## Dedicated-appliance startup and migration boundaries

- Dedicated-session Exec uses a fixed installed path without shell quotes. Debian Xsession receives the entire Exec as one argument and looks up the program using the text before the first space. Quotes become part of the filename and cause fallback to the default desktop. Official DEB CI must verify actual distribution argument parsing without starting graphical services or the machine.

- Target deployment requires explicit authorization; source changes are synchronized through Git and published packages. Follow the [local connection guide](../../docs/linuxcnc-local-connection.md) for environment and commands; do not create parallel startup scripts or rewrite machine configuration.
- The application uses installation prefix `/usr`. CMake `BETTERCNC_PROJECT_DIR` defaults to `/etc/betterlinuxcnc` and is fixed there for official releases. User services read its `launcher.json`; old `/home/teto/ArcAmberCNC/launcher.json` is only explicit migration input. Packages do not overwrite real configuration. `--check` validates configuration/dependencies, not machine connectivity.
- The fixed DEB postinst idempotently prepares accounts/directories through `betterlinuxcnc-appliance provision`. `prepare` explicitly imports machine configuration; `activate` explicitly configures dedicated login. Neither is automatically invoked by the package or launcher. LightDM runs the `betterlinuxcnc-kiosk` X11 session as `linuxcnc`; it imports actual DISPLAY/Xauthority and starts `betterlinuxcnc-launcher.service`. Do not reuse the old account's UID/Xauthority or manually start a second launcher. Even after service active, check logs, private `state.json` ready, public machine status, and the GUI window.
- The operating account HOME is `/var/lib/betterlinuxcnc/home` and cache is `/var/cache/betterlinuxcnc/user`; parent directories remain root-owned. systemd logs live in `/var/log/betterlinuxcnc/launcher/<current-start-directory>/`. `BETTERCNC_SHARE_LOGS=1` relaxes only log directory/file permissions for the maintenance group; state, sockets, and locks stay private. Direct CLI startup defaults to `.runtime/launcher/` under the configuration directory. Read controller, linuxcnc, and cam-link logs from the latest startup directory; do not hardcode old PIDs or log directories.
- `cnc-maint` reads diagnostics through fixed SSH commands only, with no arbitrary shell, service start/stop, or sudo. When changing login policy, retain an existing root maintenance session as directed by the local connection guide; do not add elevation channels through the launcher.
- Preserve existing CAM configuration. Do not upload test programs or change network-start permissions for connection checks. Uploads never implicitly start motion; use the public CAM capability contract. Successful startup does not establish CAM inbox machining or machine motion acceptance.

- The dedicated X11 session uses xset to disable automatic screensaver, blanking, and DPMS; ordinary desktop startup does not change display policy. Log failures without restarting the core. This does not establish acceptance of system sleep/resume.

## Reading and protected documentation

Follow the root [AGENT.md](../../AGENT.md) and every ancestor directory guide. Before implementation, read every Markdown file in this directory and each affected child directory, plus the relevant linked interface contracts. Inspect existing code and dependencies before choosing a location or library.

This guide and all other Markdown are protected: AI must neither change them autonomously nor proactively propose changes. An explicit human request and a second confirmation of the intended scope are required before any write. Keep documentation and explanatory comments English; never append change records, progress reports, operational logs, email addresses, key material, or credentials.

Extend an existing class/module when the new behavior belongs to it. Add a focused file/directory only for a distinct responsibility, lifecycle, interface, or privilege boundary. Reuse verified public APIs; do not invent dependencies, duplicate rules, or import sibling private internals. In long source files, bracket substantial feature-owning classes with the language-appropriate English BEGIN/END markers defined in root AGENT.md. Builds and source tests run only in GitHub CI.

## Child directory guides

- [packaging/AGENTS.md](packaging/AGENTS.md): Own command, desktop-session, autostart, and systemd user-service templates.
- [src/AGENTS.md](src/AGENTS.md): Contain the independent standard-library process/session orchestrator.
- [tests/AGENTS.md](tests/AGENTS.md): Verify installed entry points, staged installation, kiosk lifecycle, readiness, and supervision using controlled processes.
