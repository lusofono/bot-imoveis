"""Secrets: the Gmail App Password. In the Mac Keychain today; in AWS Secrets Manager later.

Nothing here writes a password to logs or to the queues, and the assistant never sees it.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import sys


def password_hash(password, salt):
    """scrypt for login passwords; standard library only. Unused while the hosted login is paused."""
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def app_password(folder, account):
    """The Gmail App Password: a 600 file if one is set (BOT_MAIL_GMAIL_PASSWORD_FILE or secrets/), else the
    Mac Keychain item "gmail_cycle" for this account. It is never logged nor given to the assistant."""
    secret_path = os.environ.get("BOT_MAIL_GMAIL_PASSWORD_FILE")
    path = Path(secret_path) if secret_path else Path(folder) / "secrets" / "gmail_app_password"
    if path.exists():
        if path.stat().st_mode & 0o077:
            raise RuntimeError("O ficheiro da App Password deve ter permissões 600.")
        password = path.read_text().strip().replace(" ", "")
    elif sys.platform == "darwin":
        result = subprocess.run(["security", "find-generic-password", "-a", account,
                                 "-s", "gmail_cycle", "-w"], capture_output=True, text=True)
        password = result.stdout.strip() if result.returncode == 0 else ""
    else:
        password = ""
    if not password:
        raise RuntimeError("Configura a App Password com mac/setup.command ou bot-mail setup.")
    return password


def save_password(folder, account, password):
    password = password.strip().replace(" ", "")
    if not password:
        raise ValueError("App Password vazia.")
    if sys.platform == "darwin":
        subprocess.run(["security", "add-generic-password", "-U", "-a", account,
                        "-s", "gmail_cycle", "-w", password], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        path = Path(folder) / "secrets" / "gmail_app_password"
        path.parent.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(password + "\n")


def has_app_password(folder, account):
    """Whether the App Password is already stored. It never returns or logs the password itself."""
    try:
        return bool(app_password(folder, account))
    except RuntimeError:
        return False
