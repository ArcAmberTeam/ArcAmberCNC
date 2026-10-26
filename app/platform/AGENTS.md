# Rust platform capabilities

Follow the root `AGENT.md` and each module's `AGENTS.md`. Build and test only in GitHub CI; do not build or run source tests locally or on the target.

- This directory groups network communication, application/firmware maintenance, and future machine configuration management by responsibility. Python machine control, the Qt backend, and startup orchestration remain in `app/controller`, `app/desktop`, and `app/launcher`.
- `cam-link`, `updater`, and `mesa-update` retain independent Cargo manifests, lockfiles, CMake install rules, public CLIs, and process/permission boundaries. The directory is not a combined daemon or shared privileged runtime.
- Collaborate only through public CLI or protocol contracts. Do not import sibling private implementations or give the network service update/configuration-write privileges.
- Installed command names, systemd unit names, runtime paths, and control protocols do not derive from this source-directory grouping.
- Configuration management requires its own agreed interface and permission model before implementation; do not scaffold placeholder services as part of directory maintenance.
- All Markdown follows the protection rules below.

## Reading and protected documentation

Follow the root [AGENT.md](../../AGENT.md) and every ancestor directory guide. Before implementation, read every Markdown file in this directory and each affected child directory, plus the relevant linked interface contracts. Inspect existing code and dependencies before choosing a location or library.

This guide and all other Markdown are protected: AI must neither change them autonomously nor proactively propose changes. An explicit human request and a second confirmation of the intended scope are required before any write. Keep documentation and explanatory comments English; never append change records, progress reports, operational logs, email addresses, key material, or credentials.

Extend an existing class/module when the new behavior belongs to it. Add a focused file/directory only for a distinct responsibility, lifecycle, interface, or privilege boundary. Reuse verified public APIs; do not invent dependencies, duplicate rules, or import sibling private internals. In long source files, bracket substantial feature-owning classes with the language-appropriate English BEGIN/END markers defined in root AGENT.md. Builds and source tests run only in GitHub CI.

## Child directory guides

- [cam-link/AGENTS.md](cam-link/AGENTS.md): CAM networking and public controller requests.
- [mesa-update/AGENTS.md](mesa-update/AGENTS.md): Mesa checks and guarded maintenance.
- [updater/AGENTS.md](updater/AGENTS.md): Application Release maintenance.
