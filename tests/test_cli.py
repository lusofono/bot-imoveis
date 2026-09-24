from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from backend.cli import main
from backend.store import save_json

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


def test_app_password_is_checked_against_gmail_before_being_stored(tmp_path, capsys):
    save_json(tmp_path / "config.json", {"account": "owner@example.com"})
    saved = []
    with patch("backend.cli.getpass.getpass", return_value="abcd efgh ijkl mnop"), \
         patch("backend.mail.connect") as connect, \
         patch("backend.cli.save_password", side_effect=lambda *args: saved.append(args)):
        assert main(["--instance", str(tmp_path), "password"]) == 0
    assert connect.call_args.args == ("owner@example.com", "abcdefghijklmnop")  # spaces are Google's own
    assert saved and "Keychain" in capsys.readouterr().out

    # A wrong password is never stored, and neither is an empty one.
    with patch("backend.cli.getpass.getpass", return_value="errada"), \
         patch("backend.mail.connect", side_effect=RuntimeError("Falhou o login IMAP.")), \
         patch("backend.cli.save_password", side_effect=lambda *args: saved.append(args)):
        assert main(["--instance", str(tmp_path), "password"]) == 1
    with patch("backend.cli.getpass.getpass", return_value="  "), \
         patch("backend.cli.save_password", side_effect=lambda *args: saved.append(args)):
        assert main(["--instance", str(tmp_path), "password"]) == 1
    assert len(saved) == 1
    assert "Falhou o login" in capsys.readouterr().err


def test_demo_command_creates_fictitious_data_without_overwriting(tmp_path):
    from backend.service import MailService
    destination = tmp_path / "demo"
    assert main(["demo", str(destination)]) == 0
    with patch("backend.service.has_app_password", return_value=False):
        metrics = MailService(destination).metrics()
    assert metrics["account"] == "demo@example.com"
    assert len(metrics["properties"]) == 2
    assert metrics["totals"]["pending"] == 7
    assert metrics["totals"]["blocked"] == 2
    original = (destination / "config.json").read_bytes()
    assert main(["demo", str(destination)]) == 1
    assert (destination / "config.json").read_bytes() == original


def test_openai_key_is_checked_against_the_api_before_being_stored(tmp_path, capsys):
    save_json(tmp_path / "config.json", {"account": "owner@example.com"})
    saved = []
    with patch("backend.cli.getpass.getpass", return_value=" sk-test-123 "), \
         patch("backend.openai_client.check_key") as check_key, \
         patch("backend.cli.save_openai_key", side_effect=lambda *args: saved.append(args)):
        assert main(["--instance", str(tmp_path), "openai-key"]) == 0
    check_key.assert_called_once_with("sk-test-123")
    assert saved == [(tmp_path, "owner@example.com", "sk-test-123")]
    assert "Keychain" in capsys.readouterr().out

    # An invalid key is never stored, and neither is an empty one.
    with patch("backend.cli.getpass.getpass", return_value="sk-errada"), \
         patch("backend.openai_client.check_key", side_effect=RuntimeError("Chave OpenAI inválida.")), \
         patch("backend.cli.save_openai_key", side_effect=lambda *args: saved.append(args)):
        assert main(["--instance", str(tmp_path), "openai-key"]) == 1
    with patch("backend.cli.getpass.getpass", return_value="  "), \
         patch("backend.cli.save_openai_key", side_effect=lambda *args: saved.append(args)):
        assert main(["--instance", str(tmp_path), "openai-key"]) == 1
    assert len(saved) == 1
    assert "inválida" in capsys.readouterr().err
