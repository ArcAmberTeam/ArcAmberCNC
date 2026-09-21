#!/bin/bash
# CI-side transport only; the VM owns installation and rollback.
set -euo pipefail
: "${STAGING_SSH_KEY:?Set the staging environment SSH key}"
: "${STAGING_KNOWN_HOSTS:?Set the pinned VM SSH host key}"
: "${STAGING_HOST:?}" "${STAGING_PORT:?}" "${STAGING_USER:?}"
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${GITHUB_RUN_ATTEMPT:?}"
[[ $GITHUB_SHA =~ ^[0-9a-f]{40}$ ]]
[[ $GITHUB_RUN_ID =~ ^[0-9]+$ && $GITHUB_RUN_ATTEMPT =~ ^[0-9]+$ ]]
[[ $STAGING_HOST =~ ^[a-zA-Z0-9.-]+$ && $STAGING_PORT =~ ^[0-9]+$ ]]
[[ $STAGING_USER == deploy ]]
artifact=$(realpath "${1:?artifact directory}")
release="$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT-$GITHUB_SHA"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
chmod 700 "$work"
printf '%s\n' "$STAGING_SSH_KEY" > "$work/key"
printf '%s\n' "$STAGING_KNOWN_HOSTS" > "$work/known_hosts"
chmod 600 "$work/key" "$work/known_hosts"
unset STAGING_SSH_KEY STAGING_KNOWN_HOSTS
ssh_options=(-i "$work/key" -o IdentitiesOnly=yes -o BatchMode=yes
  -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$work/known_hosts"
  -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=4)
# Verify the same-run artifact before selecting the runtime package.
(cd "$artifact" && sha256sum --check SHA256SUMS.txt)
mkdir "$work/bundle"
count=0
for package in "$artifact"/*.deb; do
  if [[ $(dpkg-deb -f "$package" Package) == linuxcnc-uspace ]]; then
    [[ $(dpkg-deb -f "$package" Architecture) == amd64 ]]
    cp "$package" "$work/bundle/linuxcnc-uspace.deb"
    count=$((count + 1))
  fi
done
[[ $count == 1 ]]
printf '%s\n' "$GITHUB_SHA" > "$work/bundle/COMMIT"
(cd "$work/bundle" && sha256sum COMMIT linuxcnc-uspace.deb > SHA256SUMS)
target="$STAGING_USER@$STAGING_HOST"
ssh "${ssh_options[@]}" -p "$STAGING_PORT" "$target" \
  "mkdir -m 700 /srv/betterlinuxcnc/incoming/$release"
scp "${ssh_options[@]}" -P "$STAGING_PORT" "$work/bundle/"* \
  "$target:/srv/betterlinuxcnc/incoming/$release/"
ssh "${ssh_options[@]}" -p "$STAGING_PORT" "$target" \
  "sudo /usr/local/sbin/betterlinuxcnc-deploy $release"
if [[ -n ${GITHUB_STEP_SUMMARY:-} ]]; then
  # shellcheck disable=SC2016 # Backticks format Markdown, not command substitution.
  printf 'Installed `%s` on Debian 13 PREEMPT_RT through FRP; package version verified. No simulation was run.\n' \
    "$GITHUB_SHA" >> "$GITHUB_STEP_SUMMARY"
fi
