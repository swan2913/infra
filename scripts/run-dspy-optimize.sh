#!/usr/bin/env bash
set -euo pipefail
OUT=$(/home/ksh/infra/dspy/.venv/bin/python3 /home/ksh/infra/dspy/cron_optimize.py 2>&1)
/home/ksh/infra/scripts/hermes-notify "$OUT"
