from pathlib import Path
import subprocess
import sys
from backend.cli import main

ROOT = Path(__file__).resolve().parent.parent


def test_replica_has_no_private_data_and_the_cli_works(tmp_path):
    destination = tmp_path / "person"
    assert main(["replicate", str(destination)]) == 0
    assert not (destination / "queue.json").exists()
    assert not list((destination / "secrets").iterdir())
    result = subprocess.run([sys.executable, "-m", "backend.cli", "--instance", str(destination), "read"],
                            capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 1
    assert "Configura uma conta" in result.stderr
    assert "Traceback" not in result.stderr
    assert main(["replicate", str(destination)]) == 1
