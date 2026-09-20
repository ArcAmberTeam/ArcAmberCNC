#!/bin/bash
# Container-only regression check: extract the artifact, never install it.
set -euo pipefail
cd /artifact
sha256sum --check SHA256SUMS.txt
packages=(linuxcnc-uspace_*_amd64.deb)
[[ ${#packages[@]} == 1 && -f ${packages[0]} ]]
[[ $(dpkg-deb -f "${packages[0]}" Package) == linuxcnc-uspace ]]
[[ $(dpkg-deb -f "${packages[0]}" Architecture) == amd64 ]]
dpkg-deb -x "${packages[0]}" /work/runtime
mkdir /work/bin
# The package's compiled default tool-table path belongs to an installed
# system. Supply the matching source fixture explicitly for extracted tests.
cat > /work/bin/rs274 <<'SH'
#!/bin/sh
exec /work/runtime/usr/bin/rs274 -t /source/configs/common/tool.tbl "$@"
SH
chmod +x /work/bin/rs274
export PATH="/work/bin:$PATH"
export LD_LIBRARY_PATH=/work/runtime/usr/lib
export LC_ALL=C
mkdir /work/tests
cases=(oword-bug315 namedparam-bug424 do-while-break exists
       fractional-linenumbers return-value sequence-number subs-follow-main)
for name in "${cases[@]}"; do
  cp -a "/source/tests/interp/$name" /work/tests/
  (
    cd "/work/tests/$name"
    if ! timeout 15 bash test.sh > actual 2> stderr; then
      cat actual stderr >&2
      exit 1
    fi
    diff -u expected actual
  )
  echo "PASS interpreter/$name"
done
echo "Passed ${#cases[@]} interpreter regressions from the same-run Debian artifact."
