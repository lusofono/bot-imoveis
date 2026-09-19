#!/usr/bin/env python3
"""Local start: the page on http://127.0.0.1:8765, opened in the browser. Later, the .app starts here too.

The data folder is data/ unless BOT_MAIL_INSTANCE names another one. Options: --port N and --no-browser.
The other commands (setup, read, send, stdio…) are in `bot-mail`, i.e. backend/cli.py.
"""
import sys
from backend.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["web", *sys.argv[1:]]))
