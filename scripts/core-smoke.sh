#!/bin/bash
set -euo pipefail
# Execute inside the session. The bundled 2048 core requires no ROM or BIOS.
source "${XDG_RUNTIME_DIR}/container-env"
/usr/local/bin/stop-retroarch
trap 's6-svc -u /etc/service/retroarch' EXIT
for driver in glcore vulkan; do
    override=$(mktemp)
    printf 'video_driver = "%s"\nconfig_save_on_exit = "false"\nsavestate_auto_save = "false"\n' "$driver" > "$override"
    timeout 45 retroarch --verbose --max-frames=180 \
        --config /home/ubuntu/.config/retroarch/retroarch.cfg --appendconfig "$override" \
        -L /home/ubuntu/.config/retroarch/core-bundle/cores/2048_libretro.so
    rm -f "$override"
done
