from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bot_mail.credentials import app_password, save_password
CredentialError = RuntimeError
BASE = Path(__file__).resolve().parent
def get_app_password(account):
    return app_password(BASE, account)
def save_app_password(account, password):
    return save_password(BASE, account, password)
