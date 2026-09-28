#!/bin/bash
# Own source-check tool setup for the GitHub-hosted Ubuntu x64 runner.
set -euo pipefail
: "${RUNNER_TEMP:?GitHub runner temporary directory is required}"
: "${GITHUB_PATH:?GitHub path file is required}"

# These are supplied by the ubuntu-24.04 runner image; no apt/sudo is needed.
for tool in git python3 make shellcheck curl tar sha256sum; do
  command -v "$tool" >/dev/null || {
    echo "Required hosted-runner tool is missing: $tool" >&2
    exit 1
  }
done

version=1.7.12
archive="actionlint_${version}_linux_amd64.tar.gz"
checksum=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8
download_dir=$(mktemp -d "$RUNNER_TEMP/actionlint.XXXXXX")
trap 'rm -rf "$download_dir"' EXIT
tools_dir="$RUNNER_TEMP/source-check-tools"
mkdir -p "$tools_dir"
curl --fail --silent --show-error --location --retry 3 \
  "https://github.com/rhysd/actionlint/releases/download/v${version}/${archive}" \
  --output "$download_dir/$archive"
(cd "$download_dir" && printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check -)
tar -xzf "$download_dir/$archive" -C "$tools_dir" actionlint
"$tools_dir/actionlint" -version
printf '%s\n' "$tools_dir" >> "$GITHUB_PATH"
