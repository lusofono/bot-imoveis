import argparse
import getpass
import json
import os
from pathlib import Path
import secrets
import sys
from urllib.parse import urlsplit
from .credentials import save_password
from .service import MailService
from .storage import load_json, save_json, locked

ROOT = Path(__file__).resolve().parent.parent


def ask(label, default=""):
    return input(f"{label} [{default}]: ").strip() or default


def main(argv=None):
    parser = argparse.ArgumentParser(description="bot_mail — uma conta, uma pasta, um JSON")
    parser.add_argument("--instance", type=Path, default=Path(os.environ.get("BOT_MAIL_INSTANCE", ROOT / "apalace/rent")))
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("setup", "setup-server", "read", "pending", "send", "serve", "stdio"):
        commands.add_parser(name)
    resolve = commands.add_parser("resolve")
    resolve.add_argument("message_id")
    resolve.add_argument("--was-sent", choices=["yes", "no"], required=True)
    replicate = commands.add_parser("replicate")
    replicate.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    folder = args.instance.resolve()
    service = MailService(folder)
    try:
        if args.action == "replicate":
            destination = args.destination.resolve()
            if destination.exists():
                raise ValueError("O destino já existe; não será substituído.")
            destination.mkdir(parents=True, mode=0o700)
            example = load_json(ROOT / "config.example.json", {})
            save_json(destination / "config.json", example)
            for name in ("logs", "secrets"):
                (destination / name).mkdir(mode=0o700)
            for name in ("read", "send", "setup", "setup_server", "mcp"):
                content = (ROOT / "apalace/rent" / f"{name}.py").read_text()
                # Fresh replica: source code only, never queue, credentials or OAuth state.
                (destination / f"{name}.py").write_text(content.replace("Path(__file__).resolve().parents[2]", repr(str(ROOT))))
                (destination / f"{name}.command").write_text((ROOT / "apalace/rent" / f"{name}.command").read_text().replace("../../.venv/bin/python", str(ROOT / ".venv/bin/python")))
                (destination / f"{name}.command").chmod(0o755)
            print(f"Réplica vazia criada: {destination}. Executa setup.command nela.")
        elif args.action == "setup":
            folder.mkdir(parents=True, exist_ok=True)
            cfg = load_json(folder / "config.json", load_json(ROOT / "config.example.json", {}))
            account = ask("Conta Gmail", cfg.get("account", ""))
            if "@" not in account or any(c in account for c in "\r\n"):
                raise ValueError("Conta inválida.")
            existing = load_json(folder / "queue.json", {})
            if existing and existing.get("account") != account:
                raise ValueError("Esta pasta já tem dados de outra conta. Cria uma réplica vazia.")
            subject = input(f"Assunto contém (Enter = qualquer; atual: {cfg.get('subject_contains', '')}): ").strip()
            mailbox = ask("Pasta: all ou inbox", cfg.get("mailbox", "all"))
            if mailbox not in ("all", "inbox"):
                raise ValueError("Pasta inválida.")
            lookback = int(ask("Dias da primeira leitura", str(cfg.get("lookback_days", 2))))
            if lookback < 0:
                raise ValueError("Dias inválidos.")
            password = getpass.getpass("Google App Password (Enter mantém a existente): ")
            if password:
                save_password(folder, account, password)
            cfg.update(account=account, subject_contains=subject, mailbox=mailbox,
                       lookback_days=lookback, incoming_only=True)
            save_json(folder / "config.json", cfg)
            print("Configuração guardada. Nenhum email lido ou enviado.")
        elif args.action == "setup-server":
            from .oauth import password_hash
            url = ask("URL pública HTTPS (ex.: https://mail.exemplo.pt)")
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/") or parsed.query or parsed.fragment or parsed.username:
                raise ValueError("Usa uma origem HTTPS, sem caminho.")
            redirect = ask("Callback EXATO mostrado pelo ChatGPT ao criar o MCP")
            callback = urlsplit(redirect)
            if callback.scheme != "https" or not callback.hostname or callback.fragment:
                raise ValueError("Callback HTTPS inválido.")
            password = getpass.getpass("Nova password de acesso MCP (mínimo 16 caracteres; diferente da Gmail): ")
            if len(password) < 16 or password != getpass.getpass("Repetir password MCP: "):
                raise ValueError("Passwords diferentes ou demasiado curtas.")
            salt = secrets.token_hex(16)
            secret_dir = folder / "secrets"
            secret_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            save_json(secret_dir / "login.json", {"salt": salt, "password_hash": password_hash(password, salt),
                "redirect_uris": [redirect], "public_url": url.rstrip("/")})
            # Changing login credentials must revoke existing grants.
            save_json(secret_dir / "oauth.json", {"clients": {}, "codes": {}, "access": {}, "refresh": {}})
            print("Acesso MCP configurado. Reinicia o serviço e volta a ligar o ChatGPT.")
        elif args.action == "read":
            result = service.read()
            print(json.dumps({"added": result["added"], "pending": len(result["emails"])}, ensure_ascii=False))
        elif args.action == "pending":
            print(json.dumps(service.pending(), ensure_ascii=False, indent=2))
        elif args.action == "send":
            data = service.pending()
            ids = [item["id"] for item in data["emails"] if item.get("send_reply") is True
                   and item.get("reply_text", "").strip()]
            if not ids:
                print("Nada marcado para envio. No JSON, marca send_reply=true nos rascunhos pretendidos.")
                return 0
            preview = service.preview(ids)
            print(json.dumps(preview["replies"], ensure_ascii=False, indent=2))
            if not sys.stdin.isatty() or input("Enviar este lote? Escreve ENVIAR: ") != "ENVIAR":
                print("Nenhum email enviado.")
                return 0
            print(json.dumps(service.send(preview["preview_token"], True), ensure_ascii=False))
        elif args.action == "resolve":
            service.resolve(args.message_id, args.was_sent == "yes")
            print("Resultado confirmado e JSON atualizado.")
        elif args.action == "stdio":
            from .server import create_server
            create_server(folder).run(transport="stdio")
        elif args.action == "serve":
            from .server import http_app
            import uvicorn
            settings = load_json(folder / "secrets" / "login.json", {})
            url = os.environ.get("BOT_MAIL_PUBLIC_URL", settings.get("public_url", ""))
            if not url:
                raise ValueError("Executa setup-server antes de iniciar.")
            # Only one HTTP worker per replica (OAuth state), including across shells.
            with locked(folder, "server"):
                uvicorn.run(http_app(folder, url), host=os.environ.get("BOT_MAIL_HOST", "127.0.0.1"),
                            port=int(os.environ.get("BOT_MAIL_PORT", "8000")),
                            proxy_headers=False, access_log=False)
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
