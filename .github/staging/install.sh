#!/bin/bash
# Provision this root-owned helper on the disposable staging VM, never production.
set -euo pipefail
[[ $EUID == 0 && $# == 1 && $1 =~ ^[0-9]+-[0-9]+-[0-9a-f]{40}$ ]] || exit 2
release=$1
base=/srv/betterlinuxcnc
exec 9>/run/lock/betterlinuxcnc-deploy.lock
flock -w 600 9
# shellcheck disable=SC1091 # Provided by the target Debian system.
[[ $(. /etc/os-release; printf '%s' "$VERSION_ID") == 13 ]]
[[ $(dpkg --print-architecture) == amd64 ]]
[[ $(cat /sys/kernel/realtime) == 1 ]]
if pgrep -u linuxcnc -x milltask >/dev/null; then
  echo 'Close the interactive LinuxCNC session before deploying.' >&2
  exit 1
fi
destination="$base/releases/$release"
incoming="$base/incoming/$release"
[[ -d $incoming && ! -e $destination ]]
install -d -m 755 "$destination"
for file in COMMIT linuxcnc-uspace.deb smoke.ini smoke.py SHA256SUMS; do
  [[ -f $incoming/$file && ! -L $incoming/$file ]]
  install -m 644 "$incoming/$file" "$destination/$file"
done
cd "$destination"
sha256sum --check SHA256SUMS
[[ $(cat COMMIT) == "${release##*-}" ]]
[[ $(dpkg-deb -f linuxcnc-uspace.deb Package) == linuxcnc-uspace ]]
[[ $(dpkg-deb -f linuxcnc-uspace.deb Architecture) == amd64 ]]
previous=$(readlink -f "$base/current" || true)
export DEBIAN_FRONTEND=noninteractive

smoke() {
  local location=$1
  local scratch
  scratch=$(mktemp -d /var/tmp/linuxcnc-smoke.XXXXXXXX)
  cp "$location/smoke.ini" "$location/smoke.py" "$scratch/"
  chmod 755 "$scratch/smoke.py"
  touch "$scratch/simpockets.tbl"
  chown -R linuxcnc:linuxcnc "$scratch"
  # A result marker is mandatory: a launcher exit code alone is insufficient.
  local result=0
  # shellcheck disable=SC2016 # The child shell expands its own positional argument.
  runuser -u linuxcnc -- bash -c \
    'cd "$1"; timeout --kill-after=10s 120s linuxcnc -r smoke.ini' bash "$scratch" \
    > "$location/smoke.log" 2>&1 || result=$?
  cat "$location/smoke.log"
  [[ -f $scratch/smoke-success.json ]] || result=1
  if [[ $result == 0 ]]; then
    cp "$scratch/smoke-success.json" "$location/smoke-success.json"
  fi
  rm -rf "$scratch"
  return "$result"
}

rollback() {
  local result=$?
  trap - ERR
  printf 'Deployment failed: %s\n' "$release" >&2
  if [[ -n $previous && -f $previous/linuxcnc-uspace.deb ]]; then
    if apt-get -y --no-install-recommends --allow-downgrades install \
        "$previous/linuxcnc-uspace.deb" && smoke "$previous"; then
      echo "Restored previous LinuxCNC package: $previous" >&2
    else
      echo 'ROLLBACK FAILED: inspect package state and smoke.log' >&2
    fi
  else
    echo 'First deployment failed; no previous accepted package exists.' >&2
  fi
  exit "$result"
}
trap rollback ERR
apt-get update -o APT::Update::Error-Mode=any
apt-get -y --no-install-recommends --allow-downgrades install "$destination/linuxcnc-uspace.deb"
smoke "$destination"
ln -s "$destination" "$base/.current-$release"
mv -Tf "$base/.current-$release" "$base/current"
trap - ERR
printf 'Accepted commit %s, package %s, kernel %s\n' \
  "$(cat COMMIT)" "$(dpkg-query -W -f='${Version}' linuxcnc-uspace)" "$(uname -r)"
