#!/usr/bin/env sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CAMPAIGN=${1:-standard}
if [ "$#" -ge 2 ]; then
  exec python3 "$HERE/levelupdiag.py" --target "$2" run "$CAMPAIGN"
fi
exec python3 "$HERE/levelupdiag.py" run "$CAMPAIGN"
