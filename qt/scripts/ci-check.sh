#!/bin/bash
# Public build/check/package entry point for a disposable Debian 13 container.
set -euo pipefail

qt_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
qt_build_dir="$qt_root/build"

if [[ $# -gt 1 || ( $# -eq 1 && $1 != --install-deps ) ]]; then
  echo "Usage: bash qt/scripts/ci-check.sh [--install-deps]" >&2
  exit 2
fi

if [[ ${1:-} == --install-deps ]]; then
  if [[ $(id -u) -ne 0 ]]; then
    echo "--install-deps requires root inside the disposable Debian 13 container." >&2
    exit 2
  fi
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates build-essential cmake ninja-build pkg-config dpkg-dev file python3 \
    qt6-base-dev qt6-declarative-dev qt6-declarative-dev-tools qt6-svg-dev \
    qml6-module-qtqml qml6-module-qtqml-models qml6-module-qtqml-workerscript \
    qml6-module-qtquick qml6-module-qtquick-window qml6-module-qtquick-controls \
    qml6-module-qtquick-layouts qml6-module-qtquick-templates \
    qml6-module-qtquick-shapes qml6-module-qttest fonts-noto-cjk fonts-liberation
fi

cmake -S "$qt_root" -B "$qt_build_dir" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr -DBUILD_TESTING=ON
cmake --build "$qt_build_dir" --parallel

qt_runtime_dir=$(mktemp -d "${TMPDIR:-/tmp}/betterlinuxcnc-qt-ci.XXXXXX")
qt_package_root=$(mktemp -d "${TMPDIR:-/tmp}/betterlinuxcnc-qt-package.XXXXXX")
trap 'rm -rf "$qt_runtime_dir" "$qt_package_root"' EXIT
XDG_RUNTIME_DIR="$qt_runtime_dir" ctest --test-dir "$qt_build_dir" \
  --output-on-failure --no-tests=error

# Only upload packages generated from the source checked by this invocation.
find "$qt_build_dir" -maxdepth 1 -type f -name '*.deb' -delete
(cd "$qt_build_dir" && cpack -G DEB)
packages=("$qt_build_dir"/*.deb)
[[ -f ${packages[0]} ]]
for package in "${packages[@]}"; do
  dpkg-deb --info "$package"
  dpkg-deb --contents "$package"
  dpkg-deb --extract "$package" "$qt_package_root"
  qt_smoke_log="$qt_build_dir/Testing/Temporary/package-smoke.log"
  if QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QT_QUICK_CONTROLS_STYLE=Basic \
      XDG_RUNTIME_DIR="$qt_runtime_dir" timeout 3s "$qt_package_root/usr/bin/betterlinuxcnc" \
      >"$qt_smoke_log" 2>&1; then
    qt_smoke_status=0
  else
    qt_smoke_status=$?
  fi
  cat "$qt_smoke_log"
  if [[ $qt_smoke_status -ne 124 ]]; then
    echo "The packaged application exited unexpectedly: $qt_smoke_status" >&2
    exit 1
  fi
  python3 - "$qt_smoke_log" <<'PY'
from pathlib import Path
import re
import sys

log = Path(sys.argv[1]).read_text()
if re.search(r"QQmlApplicationEngine failed|qrc:/qml/|ReferenceError:|TypeError:", log):
    sys.exit("The packaged application reported QML errors.")
print("Packaged application loaded embedded QML and remained running (timeout 124).")
PY
done
