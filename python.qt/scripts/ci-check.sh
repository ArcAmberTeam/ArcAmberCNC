#!/bin/bash
# Public build/test entry point for a disposable Debian 13 container.
set -euo pipefail

qt_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
qt_build_dir=${QT_BUILD_DIR:-"$qt_root/build"}

qt_suite=all
qt_install_deps=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-deps) qt_install_deps=true; shift ;;
    --suite)
      qt_suite=${2:?--suite requires all, desktop or qml}
      shift 2
      ;;
    *) echo "Usage: ci-check.sh [--install-deps] [--suite all|desktop|qml]" >&2; exit 2 ;;
  esac
done
case "$qt_suite" in all|desktop|qml) ;; *) echo "Unknown suite: $qt_suite" >&2; exit 2 ;; esac

if "$qt_install_deps"; then
  if [[ $(id -u) -ne 0 ]]; then
    echo "--install-deps requires root inside the disposable Debian 13 container." >&2
    exit 2
  fi
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates build-essential cmake ninja-build pkg-config python3 python3-venv \
    qt6-base-dev qt6-declarative-dev qt6-declarative-dev-tools qt6-svg-dev \
    qml6-module-qtqml qml6-module-qtqml-models qml6-module-qtqml-workerscript \
    qml6-module-qtquick qml6-module-qtquick-window qml6-module-qtquick-controls \
    qml6-module-qtquick-layouts qml6-module-qtquick-templates \
    qml6-module-qtquick-shapes qml6-module-qtquick-dialogs qml6-module-qttest \
    python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtqml \
    python3-pyside6.qtquick python3-pyside6.qtquickcontrols2 python3-pyside6.qttest \
    linuxcnc-uspace python3-opengl fonts-noto-cjk fonts-liberation
fi

if [[ $qt_suite == desktop ]]; then
  # Debian's PySide6 is shared with a disposable venv for pinned build/lint tools.
  python3 -m venv --system-site-packages "$qt_build_dir/python-ci"
  "$qt_build_dir/python-ci/bin/python" -m pip install -r "$qt_root/../backend/requirements-ci.txt"
  PYTHON="$qt_build_dir/python-ci/bin/python" bash "$qt_root/../.github/ci/python-check.sh" desktop
  exit 0
fi

cmake -S "$qt_root" -B "$qt_build_dir" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib \
  -DPython3_EXECUTABLE=/usr/bin/python3 -DBUILD_TESTING=ON
cmake --build "$qt_build_dir" --parallel

qt_runtime_dir=$(mktemp -d "${TMPDIR:-/tmp}/betterlinuxcnc-qt-ci.XXXXXX")
trap 'rm -rf "$qt_runtime_dir"' EXIT
qt_test_selection=()
if [[ $qt_suite == qml ]]; then
  qt_test_selection=(-R '^(qml-ui|qml-lint|module-boundaries|desktop-startup)$')
fi
XDG_RUNTIME_DIR="$qt_runtime_dir" ctest --test-dir "$qt_build_dir" \
  --output-on-failure --no-tests=error "${qt_test_selection[@]}"
