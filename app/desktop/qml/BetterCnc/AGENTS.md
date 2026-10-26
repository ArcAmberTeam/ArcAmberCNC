# QML capability modules

## Purpose and ownership

Group Ui, Catalog, Manual, Toolpath, Program, and Chrome by presentation responsibility.

## Interfaces and feature placement

Each child qmldir is its public API. Keep dependencies acyclic and respect the desktop guide. Add a capability only when an independent responsibility needs a boundary; update code manifests/checks within authorized code scope.

Read the [parent guide](../AGENTS.md) before changing this directory.

## Reading and protected documentation

Follow the root [AGENT.md](../../../../AGENT.md) and every ancestor directory guide. Before implementation, read every Markdown file in this directory and each affected child directory, plus the relevant linked interface contracts. Inspect existing code and dependencies before choosing a location or library.

This guide and all other Markdown are protected: AI must neither change them autonomously nor proactively propose changes. An explicit human request and a second confirmation of the intended scope are required before any write. Keep documentation and explanatory comments English; never append change records, progress reports, operational logs, email addresses, key material, or credentials.

Extend an existing class/module when the new behavior belongs to it. Add a focused file/directory only for a distinct responsibility, lifecycle, interface, or privilege boundary. Reuse verified public APIs; do not invent dependencies, duplicate rules, or import sibling private internals. In long source files, bracket substantial feature-owning classes with the language-appropriate English BEGIN/END markers defined in root AGENT.md. Builds and source tests run only in GitHub CI.

## Child directory guides

- [Catalog/AGENTS.md](Catalog/AGENTS.md): Own the Catalog singleton, menu/toolbar metadata, localized product copy, and attributed static assets.
- [Chrome/AGENTS.md](Chrome/AGENTS.md): Own menus, toolbars, dialogs, action presentation, and machine-status display.
- [Manual/AGENTS.md](Manual/AGENTS.md): Own manual/MDI controls, axis selection, jog interaction, overrides, and ManualState presentation state.
- [Program/AGENTS.md](Program/AGENTS.md): Own ProgramPanel, program text display, selection, and execution-line presentation.
- [Toolpath/AGENTS.md](Toolpath/AGENTS.md): Own interpreted-path rendering, actual traces, coordinate readouts, viewport gestures, settings, and ToolpathState.
- [Ui/AGENTS.md](Ui/AGENTS.md): Own Theme, generic controls, typography, surfaces, and vector icon drawing.
