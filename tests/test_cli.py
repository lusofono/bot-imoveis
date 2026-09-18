from pathlib import Path
import subprocess
import sys
from bot_mail.cli import main


def test_replica_has_no_private_data_and_wrappers_work(tmp_path):
    destination = tmp_path / "person"
    assert main(["replicate", str(destination)]) == 0
    assert not (destination / "queue.json").exists()
    assert not list((destination / "secrets").iterdir())
    result = subprocess.run([sys.executable, str(destination / "read.py")], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Configura uma conta" in result.stderr
    assert "Traceback" not in result.stderr
    assert main(["replicate", str(destination)]) == 1
