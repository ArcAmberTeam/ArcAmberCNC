#!/bin/bash
# Compile one native scope in a disposable Debian 13 container. Never load HAL.
set -euo pipefail
module=${1:?Usage: native-check.sh hal|motion|drivers|task|interpreter|python-extensions}
case "$module" in
  hal|motion|drivers|task|interpreter|python-extensions) ;;
  *) echo "Unknown native CI scope: $module" >&2; exit 2 ;;
esac
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
native_work=$(mktemp -d /tmp/linuxcnc-native.XXXXXX)
trap 'rm -rf "$native_work"' EXIT

# Copy source files rather than modifying the checkout or trusting old objects.
python3 "$repo_root/.github/ci/native-source-files.py" "$repo_root" \
  | tar -C "$repo_root" --null --no-recursion -T - -cf - | tar -C "$native_work" -xf -
cd "$native_work/src"
./autogen.sh
./configure --with-realtime=uspace --disable-check-runtime-deps \
  --disable-build-documentation --disable-gtk --disable-gtk2
make -j"${NATIVE_JOBS:-4}" -O -f Makefile -f "$repo_root/.github/ci/native-targets.mk" "ci-$module"

export LD_LIBRARY_PATH="$native_work/lib"
export PYTHONPATH="$native_work/lib/python"
case "$module" in
  hal)
    nm -D --defined-only ../lib/liblinuxcnchal.so | grep -w hal_init
    nm -D --defined-only ../rtlib/hal_lib.so | grep -w hal_export_funct
    ../bin/halcmd -h >/dev/null
    ;;
  motion|drivers)
    # Inspect linked ELF modules without dlopen, hardware access or RT startup.
    for library in ../rtlib/*.so; do
      file "$library"
      nm -D --defined-only "$library" | grep -w rtapi_app_main
    done
    ;;
  task)
    for program in ../bin/milltask ../bin/linuxcncsvr; do
      file "$program"
      dependencies=$(ldd "$program")
      if grep 'not found' <<< "$dependencies"; then exit 1; fi
    done
    ;;
  interpreter)
    mkdir -p "$native_work/test-bin"
    cat > "$native_work/test-bin/rs274" <<'SH'
#!/bin/sh
exec "$NATIVE_ROOT/bin/rs274" -t "$NATIVE_ROOT/configs/common/tool.tbl" "$@"
SH
    chmod +x "$native_work/test-bin/rs274"
    export NATIVE_ROOT="$native_work"
    export PATH="$native_work/test-bin:$PATH"
    cases=(oword-bug315 namedparam-bug424 do-while-break exists
           fractional-linenumbers return-value sequence-number subs-follow-main)
    for name in "${cases[@]}"; do
      (
        cd "$native_work/tests/interp/$name"
        if ! timeout 15 bash test.sh > actual 2> stderr; then
          cat actual stderr >&2
          exit 1
        fi
        diff -u expected actual
      )
      echo "PASS interpreter/$name"
    done
    ;;
  python-extensions)
    python3 "$repo_root/.github/ci/check-native-bindings.py" "$native_work/lib/python"
    ;;
esac
echo "PASS native/$module (no controller, simulator or hardware started)"
