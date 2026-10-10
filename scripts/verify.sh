#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"
oc -n "$namespace" get pods,pvc,route
oc -n "$namespace" exec deployment/retroarch -- id
oc -n "$namespace" exec deployment/retroarch -- /usr/local/bin/verify-gpu
mkdir -p "$repo_root/recovery"
oc -n "$namespace" exec deployment/retroarch -- python3 /usr/local/bin/core-bundle \
    probe --root /opt/retroarch > "$repo_root/recovery/core-loadability.json"
python3 - "$repo_root/recovery/core-loadability.json" <<'PY'
import json,sys
cores=json.load(open(sys.argv[1]))['cores']
print(f'{sum(c["loadable"] for c in cores)}/{len(cores)} cores load; see recovery/core-loadability.json')
for core in cores:
    if not core['loadable']: print(core['core'] + ': ' + core['detail'])
PY
