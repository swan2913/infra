#!/usr/bin/env bash
set -euo pipefail
OUT=$(/home/ksh/infra/dspy/.venv/bin/python3 /home/ksh/infra/dspy/cron_remind.py 2>&1)
[ -n "$OUT" ] && /home/ksh/infra/scripts/hermes-notify "$OUT" || true
