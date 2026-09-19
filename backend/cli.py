"""The terminal commands (`bot-mail`): setup, read, send, the local page and the local MCP.

The data folder is data/ in the project unless --instance or BOT_MAIL_INSTANCE names another one.
"""
import argparse
import getpass
import json
import os
from pathlib import Path
import sys
from .configure import TEMPLATES
from .secrets import save_password
from .service import MailService
from .store import load_json, save_json

ROOT = Path(__file__).resolve().parent.parent


def ask(label, default=""):
    return input(f"{label} [{default}]: ").strip() or default


def main(argv=None):
    parser = argparse.ArgumentParser(description="bot_mail — uma conta, uma pasta, um JSON")
    parser.add_argument("--instance", type=Path, default=Path(os.environ.get("BOT_MAIL_INSTANCE", ROOT / "data")),
                        help="pasta de dados (por omissão, data/)")
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("setup", "read"):
        commands.add_parser(name)
    commands.add_parser("stdio", help="MCP local por stdio, para um assistente neste computador")
    for name in ("pending", "send"):
        commands.add_parser(name).add_argument("--property", dest="property_ref", help="referência do imóvel")
    resolve = commands.add_parser("resolve")
    resolve.add_argument("message_id")
    resolve.add_argument("--was-sent", choices=["yes", "no"], required=True)
    resolve.add_argument("--property", dest="property_ref", help="referência do imóvel")
    replicate = commands.add_parser("replicate")
    replicate.add_argument("destination", type=Path)
    web = commands.add_parser("web", help="página local, sem MCP: copiar e colar no ChatGPT")
    web.add_argument("--port", type=int, default=8765)
    web.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    folder = args.instance.resolve()
    service = MailService(folder)
    try:
        if args.action == "replicate":
            destination = args.destination.resolve()
            if destination.exists():
                raise ValueError("O destino já existe; não será substituído.")
            # Fresh data folder for another account: configuration only, never queue or credentials.
            destination.mkdir(parents=True, mode=0o700)
            save_json(destination / "config.json", load_json(TEMPLATES / "config.example.json", {}))
            for name in ("logs", "secrets"):
                (destination / name).mkdir(mode=0o700)
            print(f"Pasta de dados vazia criada: {destination}. Configura-a com: bot-mail --instance {destination} setup")
        elif args.action == "setup":
            folder.mkdir(parents=True, exist_ok=True)
            cfg = load_json(folder / "config.json", load_json(TEMPLATES / "config.example.json", {}))
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
            from .configure import configure_properties, configure_voice, yes
            if (folder / "voice.json").exists() or yes("Esta pasta trabalha por imóveis (avisos de portais como o Idealista)?"):
                configure_voice(folder)
                configure_properties(folder, account)
            print("Configuração guardada. Nenhum email lido ou enviado.")
        elif args.action == "read":
            result = service.read()
            if "properties" in result:
                summary = {queue["property_ref"]: {"added": queue["added"], "pending": len(queue["emails"])}
                           for queue in result["properties"]}
                print(json.dumps({"properties": summary, "ambiguous": result["ambiguous"]}, ensure_ascii=False))
            else:
                print(json.dumps({"added": result["added"], "pending": len(result["emails"])}, ensure_ascii=False))
        elif args.action == "pending":
            print(json.dumps(service.pending(args.property_ref), ensure_ascii=False, indent=2))
        elif args.action == "send":
            ref, ids = service.marked(args.property_ref)
            if not ids:
                print("Nada marcado para envio. No JSON, marca send_reply=true nos rascunhos pretendidos.")
                return 0
            preview = service.preview(ids, ref)
            print(json.dumps(preview["replies"], ensure_ascii=False, indent=2))
            if not sys.stdin.isatty() or input("Enviar este lote? Escreve ENVIAR: ") != "ENVIAR":
                print("Nenhum email enviado.")
                return 0
            print(json.dumps(service.send(preview["preview_token"], True, ref), ensure_ascii=False))
        elif args.action == "resolve":
            service.resolve(args.message_id, args.was_sent == "yes", args.property_ref)
            print("Resultado confirmado e JSON atualizado.")
        elif args.action == "web":
            from .api import serve
            service.config()  # needs the account; the page itself shows what else is missing
            serve(folder, args.port, not args.no_browser)
        elif args.action == "stdio":
            from .mcp import create_server
            service.check()
            create_server(folder).run(transport="stdio")
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
