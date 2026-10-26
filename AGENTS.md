# Agent entry point

Read and follow [AGENT.md](AGENT.md). When modifying a module, also follow its directory's `AGENTS.md`: `app/desktop/`, `app/launcher/`, `tools/diagnostics/`, `app/cam-link/`, `app/updater/`, `src/hal/`, `src/hal/drivers/`, `src/hal/user_comps/`, and `app/controller/`.

The `$code-boundary-standards` skill is permanently disabled in this repository and is no longer a prerequisite for development, testing, or review. Continue following the architecture, public-interface, and verification rules in `AGENT.md` and each module's `AGENTS.md`.

The new GUI and real LinuxCNC integration have been installed on the target. See “Target machine and update conventions” in [AGENT.md](AGENT.md) for development and remote-update conventions, and the [local connection guide](docs/linuxcnc-local-connection.md) for installation, startup, and troubleshooting commands. Do not interpret historical “local source edits only” instructions as prohibiting remote builds, installation, or startup that the user has authorized.
