#!/bin/bash
# Container implementation; the host checkout remains read-only.
set -euo pipefail
[[ ${OUTPUT_UID:?} =~ ^[0-9]+$ && ${OUTPUT_GID:?} =~ ^[0-9]+$ ]]
trap 'ccache --show-stats; chown -R "$OUTPUT_UID:$OUTPUT_GID" /output' EXIT
mkdir -p /work/linuxcnc
tar -C /source --exclude='./artifacts' -cf - . | tar -C /work/linuxcnc -xf -
cd /work/linuxcnc
git config --global --add safe.directory "$PWD"
test "$(dpkg --print-architecture)" = amd64
ccache --zero-stats
export DEB_BUILD_OPTIONS=parallel=4
export DEBEMAIL=emc-developers@lists.sourceforge.net
export DEBFULLNAME='LinuxCNC Github CI Robot'
python3 .github/scripts/test-package-version.py
.github/scripts/build-package-arch.sh
.github/scripts/verify-clean-repo.sh ':(exclude)VERSION' ':(exclude)debian/changelog'
echo 'Build complete: no package installation or simulation suite in CI.'
cp ../*.deb /output/
(cd /output && sha256sum ./*.deb > SHA256SUMS.txt)
