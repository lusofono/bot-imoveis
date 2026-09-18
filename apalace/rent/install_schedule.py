#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import plistlib
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
LAUNCHD = BASE / "launchd"
LOGS = BASE / "logs"
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

def make_plist(label, script, hour, minute):
    python = sys.executable
    return {
        "Label": label,
        "ProgramArguments": [python, str(BASE / script)],
        "WorkingDirectory": str(BASE),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(LOGS / f"{label}.out.log"),
        "StandardErrorPath": str(LOGS / f"{label}.err.log"),
        "RunAtLoad": False,
    }

read_h, read_m = parse_time("Hora do READ de manhã")

LAUNCHD.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)
AGENTS.mkdir(parents=True, exist_ok=True)

jobs = [
    ("pt.biglearn.apalace.rent.read", "read.py", read_h, read_m),
]

for label, script, h, m in jobs:
    local = LAUNCHD / f"{label}.plist"
    with local.open("wb") as f:
        plistlib.dump(make_plist(label, script, h, m), f)

    dest = AGENTS / local.name
    if dest.exists():
        subprocess.run(["launchctl", "unload", str(dest)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dest.write_bytes(local.read_bytes())
    subprocess.run(["launchctl", "load", str(dest)], check=True)

print("\nAgendamento instalado.")
print(f"READ diário: {read_h:02d}:{read_m:02d}")
print("SEND é manual/MCP, após confirmação do lote.")
print("\nOs scripts/config/queues continuam todos neste folder.")
print("O macOS exige apenas uma cópia do .plist em ~/Library/LaunchAgents.")
