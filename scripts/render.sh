#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"
helm template retroarch "$chart" --namespace "$namespace" "$@"
