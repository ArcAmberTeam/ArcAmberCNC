#!/bin/bash
# Public entry point for desktop checks inside the disposable Debian 13 image.
set -euo pipefail
cd /workspace/frontend
mkdir -p "$HOME"

npm ci
npm run build
npm run desktop:check
npm run desktop:test

# The compiler cache may contain an earlier release. Only upload this build's deb.
rm -rf src-tauri/target/release/bundle/deb
npm run desktop:build -- --bundles deb -- --locked
packages=(src-tauri/target/release/bundle/deb/*.deb)
[[ -f ${packages[0]} ]]
for package in "${packages[@]}"; do
  dpkg-deb --info "$package"
  dpkg-deb --contents "$package"
done
