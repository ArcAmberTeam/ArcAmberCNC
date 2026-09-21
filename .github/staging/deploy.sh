#!/bin/bash
# CI transports data only; the provisioned VM owns validation and activation.
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
script_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 -I "$script_directory/web_release.py" verify-bundle "$artifact" "$GITHUB_SHA"
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
target="$STAGING_USER@$STAGING_HOST"
# Retry only idempotent transport operations, never the root installer.
transfer() {
  local attempt
  for attempt in 1 2 3; do
    if timeout --kill-after=10s 180s "$@"; then return 0; fi
    printf 'FRP transfer attempt %s/3 failed.\n' "$attempt" >&2
    if [[ $attempt -lt 3 ]]; then sleep 5; fi
  done
  return 1
}
transfer ssh "${ssh_options[@]}" -p "$STAGING_PORT" "$target" \
  "test -x /usr/local/sbin/betterlinuxcnc-deploy-web || { echo 'Staging VM needs the Web provisioning upgrade before deployment.' >&2; exit 78; }; mkdir -p -m 700 /srv/betterlinuxcnc-web/incoming/$release"
echo 'Uploading the static Web artifact through FRP...'
transfer scp "${ssh_options[@]}" -P "$STAGING_PORT" \
  "$artifact/web.tar.gz" "$artifact/COMMIT" "$artifact/SHA256SUMS" \
  "$target:/srv/betterlinuxcnc-web/incoming/$release/"
echo 'Upload complete; validating, activating, and checking the Web release...'
ssh "${ssh_options[@]}" -p "$STAGING_PORT" "$target" \
  "sudo /usr/local/sbin/betterlinuxcnc-deploy-web $release"
if [[ -n ${GITHUB_STEP_SUMMARY:-} ]]; then
  # shellcheck disable=SC2016 # Backticks format Markdown, not command substitution.
  printf 'Published Web commit `%s` through FRP; local HTTP index and build-info verified.\n' \
    "$GITHUB_SHA" >> "$GITHUB_STEP_SUMMARY"
fi
