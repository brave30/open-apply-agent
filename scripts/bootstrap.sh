#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pin=9a120949aca3e58a2628f4b4e6edd0474d984873
if [ ! -d vendor/OpenWebRL/.git ]; then
  git clone https://github.com/OpenWebRL/OpenWebRL.git vendor/OpenWebRL
  git -C vendor/OpenWebRL checkout "$pin"
fi
test "$(git -C vendor/OpenWebRL rev-parse HEAD)" = "$pin"
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m playwright install chromium
echo 'Ready. Run .venv/bin/python -m auto_apply.cli demo'
