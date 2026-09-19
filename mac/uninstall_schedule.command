#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${BOT_MAIL_PYTHON:-.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  printf 'Executa install.command na raiz ou define BOT_MAIL_PYTHON.\n' >&2
  exit 1
fi
exec "$PYTHON" mac/uninstall_schedule.py
