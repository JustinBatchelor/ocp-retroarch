#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"
"$repo_root/scripts/preflight.sh" "$@"
oc -n "$namespace" get secret retroarch-login >/dev/null
rendered=$(mktemp)
trap 'rm -f "$rendered"' EXIT
"$repo_root/scripts/render.sh" "$@" > "$rendered"
oc apply --dry-run=server -f "$rendered" >/dev/null
helm upgrade --install retroarch "$chart" --namespace "$namespace" \
    --wait --timeout 15m "$@"
oc -n "$namespace" rollout status daemonset/retroarch-gpu-plugin --timeout=3m
oc -n "$namespace" rollout status deployment/retroarch --timeout=5m
