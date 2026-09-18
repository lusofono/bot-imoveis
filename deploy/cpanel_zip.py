"""Build the package for a cPanel hosting account: bot-imoveis-cpanel-YYYYMMDD.zip.

    .venv/bin/bot-mail --instance apalace/rent web-password    # once: the page address and password
    .venv/bin/python deploy/cpanel_zip.py

Extract it in the account's home folder (never in public_html) and follow docs/CPANEL.md, which goes
into the zip as LEIA-PRIMEIRO.md. The zip holds the page, the instance configuration and the page
password hash. It never holds the Gmail App Password, queues, logs or customer emails. Keep it private.
"""
from datetime import date, datetime
import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTANCE = ROOT / "apalace" / "rent"


def add(archive, name, data, mode):
    info = zipfile.ZipInfo(f"bot_mail/{name}", date_time=datetime.now().timetuple()[:6])
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data)


def main():
    if not (INSTANCE / "secrets" / "web.json").exists():
        sys.exit("Falta a password da página: .venv/bin/bot-mail --instance apalace/rent web-password")
    code = [ROOT / "passenger_wsgi.py", ROOT / "requirements-cpanel.txt"]
    code += sorted(path for path in (ROOT / "bot_mail").iterdir() if path.suffix in (".py", ".html"))
    instance = [INSTANCE / name for name in ("config.json", "voice.json", "secrets/web.json")]
    for folder in sorted(path for path in (INSTANCE / "properties").iterdir() if path.is_dir()):
        # Profiles and knowledge only: a queue holds customer emails and stays where it is.
        instance += sorted(path for path in folder.rglob("*") if path.is_file()
                           and path.name != "queue.json" and not path.name.startswith("."))
    out = ROOT / f"bot-imoveis-cpanel-{date.today():%Y%m%d}.zip"
    with zipfile.ZipFile(out, "w") as archive:
        add(archive, "LEIA-PRIMEIRO.md", (ROOT / "docs" / "CPANEL.md").read_bytes(), 0o644)
        for path in code:
            add(archive, path.relative_to(ROOT).as_posix(), path.read_bytes(), 0o644)
        for path in instance:
            add(archive, path.relative_to(ROOT).as_posix(), path.read_bytes(), 0o600)
    print(f"{out.name}: {len(code) + len(instance) + 1} ficheiros. Tem a configuração e o hash da password "
          "da página: guarda-o em privado e apaga-o depois de o enviares.")


if __name__ == "__main__":
    main()
