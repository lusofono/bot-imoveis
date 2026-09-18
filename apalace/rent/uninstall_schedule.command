#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
exec "${BOT_MAIL_PYTHON:-../../.venv/bin/python}" uninstall_schedule.py
