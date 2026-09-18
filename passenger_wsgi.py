"""Entry point for cPanel «Setup Python App» (Phusion Passenger).

Passenger speaks WSGI and the page is ASGI (Starlette), so a2wsgi bridges them. Only the copy-and-paste
page runs here, behind the password set with `bot-mail web-password`; the MCP server needs its own
server (see docs/SERVER.md). The instance lives next to this file, outside public_html, so the
configuration, queues and secrets are never served as files.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from a2wsgi import ASGIMiddleware  # noqa: E402
from bot_mail.web import hosted_app  # noqa: E402

application = ASGIMiddleware(hosted_app(Path(os.environ.get("BOT_MAIL_INSTANCE", ROOT / "apalace" / "rent"))))
