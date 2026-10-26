# Isolated program interpretation

## Purpose and ownership

Adapt the native gcode extension into bounded preview geometry through parse_program and the preview CLI.

## Interfaces and feature placement

Keep canonical geometry adaptation separate from parser/process entry points. Do not duplicate the interpreter, send machine commands, or import desktop/service internals.

Read the [parent guide](../AGENTS.md) before changing this directory.

## Reading and protected documentation

Follow the root [AGENT.md](../../../../AGENT.md) and every ancestor directory guide. Before implementation, read every Markdown file in this directory and each affected child directory, plus the relevant linked interface contracts. Inspect existing code and dependencies before choosing a location or library.

This guide and all other Markdown are protected: AI must neither change them autonomously nor proactively propose changes. An explicit human request and a second confirmation of the intended scope are required before any write. Keep documentation and explanatory comments English; never append change records, progress reports, operational logs, email addresses, key material, or credentials.

Extend an existing class/module when the new behavior belongs to it. Add a focused file/directory only for a distinct responsibility, lifecycle, interface, or privilege boundary. Reuse verified public APIs; do not invent dependencies, duplicate rules, or import sibling private internals. In long source files, bracket substantial feature-owning classes with the language-appropriate English BEGIN/END markers defined in root AGENT.md. Builds and source tests run only in GitHub CI.
