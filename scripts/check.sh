#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"
cd "$repo_root"
for script in scripts/*.sh container/session-ready container/stop-retroarch; do sh -n "$script"; done
for script in container/session-entrypoint container/run-* container/verify-gpu; do bash -n "$script"; done
helm lint "$chart" \
    --set image.digest=sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    --set gpu.plugin.digest=sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
"${RETROARCH_PYTHON:-python3}" -m unittest discover -s tests -v
python3 scripts/core-bundle.py verify
