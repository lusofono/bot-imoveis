#!/usr/bin/env python3
"""Schedules READ once a day on the Mac (launchd). SEND is never scheduled: it needs approval."""
from __future__ import annotations

import os
import sys
import plistlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("BOT_MAIL_INSTANCE", ROOT / "data")).resolve()
LAUNCHD = DATA / "launchd"
LOGS = DATA / "logs"
AGENTS = Path.home() / "Library" / "LaunchAgents"

def parse_time(label):
    while True:
        value = input(f"{label} (HH:MM, 24h): ").strip()
        try:
            h, m = value.split(":")
            h, m = int(h), int(m)
            if 0 <= h <= 23 and 0 <= m <= 59:
                return h, m
        except Exception:
            pass
        print("Formato inválido. Exemplo: 08:00 ou 19:00")

def make_plist(label, command, hour, minute):
    python = sys.executable
    return {
        "Label": label,
        "ProgramArguments": [python, "-m", "backend.cli", "--instance", str(DATA), command],
        "WorkingDirectory": str(ROOT),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(LOGS / f"{label}.out.log"),
        "StandardErrorPath": str(LOGS / f"{label}.err.log"),
        "RunAtLoad": False,
    }

if not (DATA / "config.json").exists():
    sys.exit(f"Configura primeiro a pasta de dados ({DATA}) com mac/setup.command.")

read_h, read_m = parse_time("Hora do READ de manhã")

LAUNCHD.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)
AGENTS.mkdir(parents=True, exist_ok=True)

jobs = [
    ("pt.biglearn.apalace.rent.read", "read", read_h, read_m),
]

for label, command, h, m in jobs:
    local = LAUNCHD / f"{label}.plist"
    with local.open("wb") as f:
        plistlib.dump(make_plist(label, command, h, m), f)

    dest = AGENTS / local.name
    if dest.exists():
        subprocess.run(["launchctl", "unload", str(dest)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dest.write_bytes(local.read_bytes())
    subprocess.run(["launchctl", "load", str(dest)], check=True)

print("\nAgendamento instalado.")
print(f"READ diário: {read_h:02d}:{read_m:02d}")
print("SEND é manual/MCP, após confirmação do lote.")
print(f"\nOs dados continuam em {DATA}.")
print("O macOS exige apenas uma cópia do .plist em ~/Library/LaunchAgents.")
