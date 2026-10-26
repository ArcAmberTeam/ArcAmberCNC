# Mesa executable entry points

## Purpose and ownership

Own separate betterlinuxcnc-mesa-update and betterlinuxcnc-mesa-flash binary wrappers.

## Interfaces and feature placement

Delegate to the corresponding public library entry point. Do not duplicate gates or allow the low-privilege check command to perform writes.

Read the [parent guide](../AGENTS.md) before changing this directory.

## Reading and protected documentation

Follow the root [AGENT.md](../../../../../AGENT.md) and every ancestor directory guide. Before implementation, read every Markdown file in this directory and each affected child directory, plus the relevant linked interface contracts. Inspect existing code and dependencies before choosing a location or library.

This guide and all other Markdown are protected: AI must neither change them autonomously nor proactively propose changes. An explicit human request and a second confirmation of the intended scope are required before any write. Keep documentation and explanatory comments English; never append change records, progress reports, operational logs, email addresses, key material, or credentials.

Extend an existing class/module when the new behavior belongs to it. Add a focused file/directory only for a distinct responsibility, lifecycle, interface, or privilege boundary. Reuse verified public APIs; do not invent dependencies, duplicate rules, or import sibling private internals. In long source files, bracket substantial feature-owning classes with the language-appropriate English BEGIN/END markers defined in root AGENT.md. Builds and source tests run only in GitHub CI.
