# Product application modules

## Purpose and ownership

Compose independently owned desktop, controller, launcher, and platform capabilities. Root CMake coordinates application installation; native LinuxCNC remains under src/.

## Interfaces and feature placement

Choose the module by responsibility, lifecycle, and permissions. Cross-module calls use public packages, CLIs, or protocols; do not create a shared privileged runtime.

Read the [parent guide](../AGENTS.md) before changing this directory.

## Reading and protected documentation

Follow the root [AGENT.md](../AGENT.md) and every ancestor directory guide. Before implementation, read every Markdown file in this directory and each affected child directory, plus the relevant linked interface contracts. Inspect existing code and dependencies before choosing a location or library.

This guide and all other Markdown are protected: AI must neither change them autonomously nor proactively propose changes. An explicit human request and a second confirmation of the intended scope are required before any write. Keep documentation and explanatory comments English; never append change records, progress reports, operational logs, email addresses, key material, or credentials.

Extend an existing class/module when the new behavior belongs to it. Add a focused file/directory only for a distinct responsibility, lifecycle, interface, or privilege boundary. Reuse verified public APIs; do not invent dependencies, duplicate rules, or import sibling private internals. In long source files, bracket substantial feature-owning classes with the language-appropriate English BEGIN/END markers defined in root AGENT.md. Builds and source tests run only in GitHub CI.

## Child directory guides

- [controller/AGENTS.md](controller/AGENTS.md): Machine operation policy, Unix service, and isolated preview.
- [desktop/AGENTS.md](desktop/AGENTS.md): Qt Quick presentation and Python adapters.
- [launcher/AGENTS.md](launcher/AGENTS.md): Process and session orchestration.
- [platform/AGENTS.md](platform/AGENTS.md): Independent Rust platform capabilities.
