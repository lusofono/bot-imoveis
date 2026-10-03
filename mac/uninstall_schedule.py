#!/usr/bin/env python3
"""Removes the daily READ from launchd. The data folder is not touched."""
from pathlib import Path
import subprocess

AGENTS = Path.home() / "Library" / "LaunchAgents"
for label in ("pt.biglearn.apalace.rent.read", "pt.biglearn.apalace.rent.send"):
    p = AGENTS / f"{label}.plist"
    if p.exists():
        subprocess.run(["launchctl", "unload", str(p)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.unlink()
        print("Removido:", p)
print("Agendamento removido. Os ficheiros/queues não foram apagados.")
