#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"
oc create namespace "$namespace" --dry-run=client -o yaml | oc apply -f -
oc -n "$namespace" create serviceaccount image-publisher --dry-run=client -o yaml | oc apply -f -
oc -n "$namespace" create rolebinding image-publisher \
    --clusterrole=system:image-builder --serviceaccount="$namespace:image-publisher" \
    --dry-run=client -o yaml | oc apply -f -
# Generate only on first installation; never rotate credentials on a routine deploy.
if ! oc -n "$namespace" get secret retroarch-login >/dev/null 2>&1; then
    auth_dir=$(mktemp -d)
    trap 'rm -rf "$auth_dir"' EXIT
    chmod 700 "$auth_dir"
    printf '%s' justin > "$auth_dir/username"
    openssl rand -hex 24 | tr -d '\n' > "$auth_dir/password"
    oc -n "$namespace" create secret generic retroarch-login \
        --from-file=username="$auth_dir/username" --from-file=password="$auth_dir/password"
fi
printf 'Login is stored in Secret retroarch/retroarch-login. Use scripts/show-login.sh to retrieve it privately.\n'
