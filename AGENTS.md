# Agent entry point

Read and follow [AGENT.md](AGENT.md) before any work. It defines the project map, architecture, feature-placement rules, English-only comments and PR format, and verification constraints.

AI must not independently create local or remote branches, including via worktrees or automation. Commit and push only to the human-designated branch or the established `kihon` branch, then use the authorized PR-to-`main` flow. Task isolation is not permission to create a branch. Preserve unrelated work; report branch/PR conflicts instead of inventing another branch. See the full Git rules in [AGENT.md](AGENT.md#git-and-pull-request-requirements).

All Markdown, including this file and `AGENT.md`, is protected. AI must not autonomously change it or proactively propose changes. Only an explicit human request followed by a second confirmation of the intended scope permits a write. Coding, PR, and merge authorization do not grant Markdown permission. Never append change records, progress reports, operational logs, email addresses, key material, or credentials to Markdown.

Read every Markdown file directly in each directory along the root-to-target path, and in every affected child directory. Follow the owner guides and relevant linked architecture/interface contracts before implementation. Start application work at [app/AGENTS.md](app/AGENTS.md); root `AGENT.md` also routes native, tool, configuration, and CI work.

The `$code-boundary-standards` skill is permanently disabled in this repository. Continue following the architecture, public interfaces, and verification requirements in `AGENT.md` and scoped `AGENTS.md` files.

Builds and source tests run only in GitHub-hosted CI, never locally or on the target. Deployment uses published packages and explicit task authorization; it does not authorize motion. See [target conventions](AGENT.md#target-machine-and-update-conventions) and the [local connection guide](docs/linuxcnc-local-connection.md).
