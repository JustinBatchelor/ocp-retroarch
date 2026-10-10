#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"
oc get clusterversion version --request-timeout=10s
oc get node worker-0 --request-timeout=10s
oc get storageclass truenas-nfs --request-timeout=10s
management_pod=$(oc -n openshift-machine-config-operator get pods \
    -l k8s-app=machine-config-daemon --field-selector spec.nodeName=worker-0 \
    -o jsonpath='{.items[0].metadata.name}')
oc -n openshift-machine-config-operator exec "$management_pod" -c machine-config-daemon -- sh -ec '
    test "$(cat /rootfs/sys/class/drm/renderD128/device/vendor)" = 0x1002
    test "$(cat /rootfs/sys/class/drm/renderD128/device/device)" = 0x731f
    test "$(basename "$(readlink /rootfs/sys/class/drm/renderD128/device/driver)")" = amdgpu
    test "$(readlink -f /rootfs/sys/class/drm/card0/device)" = "$(readlink -f /rootfs/sys/class/drm/renderD128/device)"
    stat -c "%g %n" /rootfs/dev/dri/card0 /rootfs/dev/dri/renderD128
'
oc describe node worker-0 | sed -n '/Allocated resources:/,$p'
python3 "$repo_root/scripts/core-bundle.py" verify
helm lint "$chart" "$@"
printf 'Preflight passed. Check worker headroom and TrueNAS dataset free space before rollout.\n'
