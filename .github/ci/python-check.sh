#!/bin/bash
# Public CI scopes for the installed Python packages; vendor seams stay in tests.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
scope=${1:?Usage: python-check.sh service|preview|desktop}
python_bin=${PYTHON:-python3}
case "$scope" in
  service)
    package=python.service
    paths=(python.service/src/betterlinuxcnc_service python.service/src/bettercnc_controller
           python.service/tests/test_service.py python.service/tests/test_control_service.py python.service/tests/test_controller.py)
    tests=(test_service.py test_control_service.py test_controller.py)
    test_dir=python.service/tests
    ;;
  preview)
    package=python.service
    paths=(python.service/src/bettercnc_preview python.service/tests/test_preview.py)
    tests=(test_preview.py)
    test_dir=python.service/tests
    # Missing native extensions must fail here, never silently skip real RS274 tests.
    "$python_bin" -c 'import gcode, linuxcnc; print(gcode.__file__, linuxcnc.__file__)'
    ;;
  desktop)
    package=python.desktop
    paths=(python.desktop/python python.desktop/tests/python python.desktop/scripts python.desktop/app/main.py python.desktop/setup.py)
    tests=(test_session.py test_desktop.py)
    test_dir=python.desktop/tests/python
    export QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QT_QUICK_CONTROLS_STYLE=Basic
    ;;
  *) echo "Unknown Python CI scope: $scope" >&2; exit 2 ;;
esac
"$python_bin" -m ruff check "${paths[@]}"
"$python_bin" -m ruff format --check "${paths[@]}"
"$python_bin" python.desktop/scripts/check_boundaries.py
package_dist=$(mktemp -d)
trap 'rm -rf "$package_dist"' EXIT
"$python_bin" -m build --no-isolation --outdir "$package_dist" "$package"
"$python_bin" -m pip install --no-deps --force-reinstall "$package_dist"/*.whl
for test_file in "${tests[@]}"; do
  env -u PYTHONPATH "$python_bin" -m unittest discover -s "$test_dir" -p "$test_file" -v
done
mkdir -p "$package/dist"
cp "$package_dist"/* "$package/dist/"
