#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"
base=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["selkies_base"])' "$repo_root/images.lock.json")
python3 "$repo_root/scripts/core-bundle.py" verify
podman build --platform linux/amd64 --build-arg "SELKIES_BASE=$base" \
    -f "$repo_root/container/Containerfile" -t localhost/retroarch:0.1.0 "$repo_root"
test "$(podman image inspect localhost/retroarch:0.1.0 --format '{{.Os}}/{{.Architecture}}')" = linux/amd64
