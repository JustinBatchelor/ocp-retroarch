#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"
registry=$(oc -n openshift-image-registry get route default-route -o jsonpath='{.spec.host}')
plugin=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["device_plugin_image"])' "$repo_root/images.lock.json")
mkdir -p "$repo_root/recovery"
auth_dir=$(mktemp -d)
trap 'rm -rf "$auth_dir"' EXIT
oc -n "$namespace" create token image-publisher --duration=1h |
    podman login --authfile "$auth_dir/auth.json" --username image-publisher --password-stdin "$registry"
podman pull --platform linux/amd64 "$plugin"
build_id=$(podman image inspect localhost/retroarch:0.1.0 --format '{{.Id}}' | sed 's/^sha256://' | cut -c1-16)
podman push --authfile "$auth_dir/auth.json" --digestfile "$repo_root/recovery/plugin.digest" \
    "$plugin" "docker://$registry/$namespace/generic-device-plugin:2cc50b0"
podman push --authfile "$auth_dir/auth.json" --digestfile "$repo_root/recovery/app.digest" \
    localhost/retroarch:0.1.0 "docker://$registry/$namespace/retroarch:build-$build_id"
python3 - "$repo_root" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1])
app=(p/'recovery/app.digest').read_text().strip()
plugin=(p/'recovery/plugin.digest').read_text().strip()
values={'image': {'digest': app}, 'gpu': {'plugin': {'digest': plugin}}}
(p/'deployment.lock.json').write_text(json.dumps(values,indent=2)+'\n')
PY
printf 'Mirrored images. Deploy with scripts/deploy.sh -f deployment.lock.json\n'
