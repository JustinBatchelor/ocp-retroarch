#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"
# Intentionally interactive: never collect this output in validation logs.
[ -t 1 ] || { echo 'Run this in your own terminal to display the login.' >&2; exit 1; }
oc -n "$namespace" get secret retroarch-login -o json | python3 -c '
import base64,json,sys
d=json.load(sys.stdin)["data"]
for key in ("username", "password"):
    print(key + ": " + base64.b64decode(d[key]).decode())
'
