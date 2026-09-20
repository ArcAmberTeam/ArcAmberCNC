#!/bin/bash
set -euo pipefail
suite=${1:?suite}
dist=${2:?Debian release}
[[ ${OUTPUT_UID:?} =~ ^[0-9]+$ && ${OUTPUT_GID:?} =~ ^[0-9]+$ ]]
trap 'chown -R "$OUTPUT_UID:$OUTPUT_GID" /output' EXIT
if [[ $dist == bullseye ]]; then
  printf '%s\n' \
    'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20260831T235959Z/ bullseye main' \
    'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/20260831T235959Z/ bullseye-security main' \
    > /etc/apt/sources.list
  rm -f /etc/apt/sources.list.d/debian.sources
fi
apt-get -q -o Acquire::Retries=3 -o APT::Update::Error-Mode=any update
apt-get --yes --no-install-recommends install \
  ca-certificates curl git lsb-release python3 devscripts sudo adduser xauth eatmydata
mkdir -p /work/linuxcnc
tar -C /source --exclude='./artifacts' --exclude='./checked-artifact' \
  --exclude='./compat-artifacts' -cf - . | tar -C /work/linuxcnc -xf -
cd /work/linuxcnc
git config --global --add safe.directory "$PWD"
export DEB_BUILD_OPTIONS=parallel=4
export DEBEMAIL=emc-developers@lists.sourceforge.net
export DEBFULLNAME='LinuxCNC Github CI Robot'
adduser --disabled-password --gecos '' testrunner
passwd -d testrunner
adduser testrunner sudo

verify_package() {
  .github/scripts/verify-clean-repo.sh ':(exclude)VERSION' ':(exclude)debian/changelog'
}
collect_packages() {
  cp ../*.deb ../*.changes ../*.buildinfo /output/
  (cd /output && sha256sum ./*.deb ./*.changes ./*.buildinfo > SHA256SUMS.txt)
}

case "$suite" in
  gcc|clang|rtai|html)
    if [[ $suite == rtai ]]; then .github/scripts/install-rtai.sh "$dist"; fi
    eatmydata .github/scripts/install-deps.sh
    chown -R testrunner:testrunner /work/linuxcnc
    if [[ $suite == html ]]; then
      runuser -u testrunner -- .github/scripts/build-doc.sh
      .github/scripts/verify-clean-repo.sh ':(exclude)docs/po/*.po' ':(exclude)docs/po/documentation.pot'
      tar -czf /output/linuxcnc-doc.tar.gz -C docs html
    else
      realtime=uspace
      if [[ $suite == rtai ]]; then
        rtai_dirs=(/usr/realtime-*)
        [[ ${#rtai_dirs[@]} == 1 && -d ${rtai_dirs[0]} ]]
        realtime=${rtai_dirs[0]}
      fi
      compiler=(CC=gcc CXX=g++)
      if [[ $suite == clang ]]; then compiler=(CC=clang CXX=clang++); fi
      runuser -u testrunner -- env "${compiler[@]}" .github/scripts/build-rip.sh "--with-realtime=$realtime"
      .github/scripts/verify-clean-repo.sh
      if [[ $suite != rtai ]]; then
        runuser -u testrunner -- scripts/rip-environment runtests -p
        .github/scripts/verify-clean-repo.sh
      fi
    fi
    ;;
  package-arch)
    eatmydata .github/scripts/build-package-arch.sh
    verify_package
    eatmydata apt-get --yes --no-install-recommends install ../*.deb
    find tests -type d -exec chmod 0777 {} +
    runuser -u testrunner -- ./scripts/runtests -p ./tests
    verify_package
    collect_packages
    ;;
  package-indep)
    if [[ $dist == bullseye ]]; then .github/scripts/add-linuxcnc-repository.sh "$dist"; fi
    eatmydata .github/scripts/build-package-indep.sh
    .github/scripts/verify-clean-repo.sh ':(exclude)VERSION' ':(exclude)debian/changelog' \
      ':(exclude)docs/po/*.po' ':(exclude)docs/po/documentation.pot'
    eatmydata apt-get --yes --no-install-recommends install ../*.deb
    collect_packages
    ;;
  *) exit 2 ;;
esac
