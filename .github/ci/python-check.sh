#!/bin/bash
# Public CI scopes for the installed Python packages; vendor seams stay in tests.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
scope=${1:?Usage: python-check.sh service|preview|desktop}
python_bin=${PYTHON:-python3}
case "$scope" in
  service)
    package=backend
    paths=(backend/src/betterlinuxcnc_service backend/src/bettercnc_controller
           backend/tests/test_service.py backend/tests/test_control_service.py backend/tests/test_controller.py)
    tests=(test_service.py test_control_service.py test_controller.py)
    test_dir=backend/tests
    ;;
  preview)
    package=backend
    paths=(backend/src/bettercnc_preview backend/tests/test_preview.py)
    tests=(test_preview.py)
    test_dir=backend/tests
    # Missing native extensions must fail here, never silently skip real RS274 tests.
    "$python_bin" -c 'import gcode, linuxcnc; print(gcode.__file__, linuxcnc.__file__)'
    ;;
  desktop)
    package=python.qt
    paths=(python.qt/python python.qt/tests/python python.qt/scripts python.qt/app/main.py python.qt/setup.py)
    tests=(test_session.py test_desktop.py)
    test_dir=python.qt/tests/python
    export QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QT_QUICK_CONTROLS_STYLE=Basic
    ;;
  *) echo "Unknown Python CI scope: $scope" >&2; exit 2 ;;
esac
"$python_bin" -m ruff check "${paths[@]}"
"$python_bin" -m ruff format --check "${paths[@]}"
"$python_bin" python.qt/scripts/check_boundaries.py
package_dist=$(mktemp -d)
trap 'rm -rf "$package_dist"' EXIT
"$python_bin" -m build --no-isolation --outdir "$package_dist" "$package"
"$python_bin" -m pip install --no-deps --force-reinstall "$package_dist"/*.whl
for test_file in "${tests[@]}"; do
  env -u PYTHONPATH "$python_bin" -m unittest discover -s "$test_dir" -p "$test_file" -v
done
mkdir -p "$package/dist"
cp "$package_dist"/* "$package/dist/"
