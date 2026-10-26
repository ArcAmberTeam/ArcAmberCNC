# Rust platform capabilities

Follow the root `AGENT.md` and each module's `AGENTS.md`. Build and test only in GitHub CI; do not build or run source tests locally or on the target.

- This directory groups network communication, application/firmware maintenance, and future machine configuration management by responsibility. Python machine control, the Qt backend, and startup orchestration remain in `app/controller`, `app/desktop`, and `app/launcher`.
- `cam-link`, `updater`, and `mesa-update` retain independent Cargo manifests, lockfiles, CMake install rules, public CLIs, and process/permission boundaries. The directory is not a combined daemon or shared privileged runtime.
- Collaborate only through public CLI or protocol contracts. Do not import sibling private implementations or give the network service update/configuration-write privileges.
- Installed command names, systemd unit names, runtime paths, and control protocols do not derive from this source-directory grouping.
- Configuration management requires its own agreed interface and permission model before implementation; do not scaffold placeholder services as part of directory maintenance.
- README files remain manually maintained.
