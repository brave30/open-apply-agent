#!/usr/bin/env bash
set -euo pipefail
OPEN_APPLY_ROOT=${OPEN_APPLY_ROOT:-/data01/tmalekar/open-apply}
source "$OPEN_APPLY_ROOT/env.sh"
set -a
source "$OPEN_APPLY_ROOT/worker.env"
set +a
umask 077
cd "$OPEN_APPLY_ROOT/app"
exec 8>"$OPEN_APPLY_ROOT/logs/worker.lock"
flock -n 8 || exit 0
exec python -m auto_apply.worker
