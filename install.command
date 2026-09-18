#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -e .
printf '\nInstalado. Configura a conta com apalace/rent/setup.command\n'
