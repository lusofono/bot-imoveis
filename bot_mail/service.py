"""Shared implementation for MCP and local commands. No AI SDK or API."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets
import smtplib
import time
from .credentials import app_password
from .gmail import read_messages
from .reply import build_reply
from .storage import locked, load_json, save_json


def now():
    return datetime.now(timezone.utc).isoformat()


def message_key(item):
    for field in ("gmail_message_id", "message_id", "id"):
        if item.get(field):
            return str(item[field]).strip()
    raise ValueError("Email sem identificador estável.")


class MailService:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.path = self.folder / "queue.json"

    def config(self):
        cfg = load_json(self.folder / "config.json", {})
        account = cfg.get("account", "")
        if not account or "@" not in account or any(c in account for c in "\r\n"):
            raise ValueError("Configura uma conta válida antes de usar.")
        return cfg

    def load(self):
        account = self.config()["account"]
        data = load_json(self.path, {"account": account, "created_at": now(),
                                    "revision": 0, "emails": [], "replied_message_ids": []})
        if data.get("account") != account:
            raise ValueError("A conta do JSON difere da configuração. Usa uma pasta por conta.")
        for item in data["emails"]:
            item["id"] = message_key(item)
        data.setdefault("revision", 0)
        data.setdefault("replied_message_ids", [])
        return data

    def save(self, data):
        data["revision"] += 1
        data["updated_at"] = now()
        data.setdefault("stats", {})["emails_in_queue"] = len(data["emails"])
        save_json(self.path, data)

    def log(self, event, **fields):
        # No bodies, passwords, OAuth tokens, subjects or recipient addresses in logs.
        folder = self.folder / "logs"
        folder.mkdir(mode=0o700, exist_ok=True)
        import os
        fd = os.open(folder / "events.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as stream:
            stream.write(json.dumps({"at": now(), "event": event, **fields}) + "\n")

    def pending(self):
        with locked(self.folder):
            data = self.load()
            return {"revision": data["revision"], "account": data["account"],
                    "emails": data["emails"], "last_read_at": data.get("last_read_at")}

    def read(self):
        with locked(self.folder):
            cfg = self.config()
            data = self.load()
            start_at = now()
            start = datetime.now(timezone.utc).date() - timedelta(days=max(0, int(cfg.get("lookback_days", 2))))
            if data.get("last_read_at"):
                # One-day overlap handles date boundaries; IDs remove duplicates.
                start = min(start, datetime.fromisoformat(data["last_read_at"]).date() - timedelta(days=1))
            messages, scanned, mailbox = read_messages(
                cfg["account"], app_password(self.folder, cfg["account"]),
                cfg.get("subject_contains", ""), start.isoformat(),
                datetime.now(timezone.utc).date().isoformat(),
                mailbox=cfg.get("mailbox", "all"), incoming_only=cfg.get("incoming_only", True))
            known = {message_key(e) for e in data["emails"]} | set(data["replied_message_ids"])
            count = 0
            for item in messages:
                key = message_key(item)
                if key in known:
                    continue
                item.update(id=key, reply_text="", send_reply=False, reply_status="pending")
                data["emails"].append(item)
                known.add(key)
                count += 1
            data["last_read_at"] = start_at
            data["stats"] = {"new_this_read": count, "scanned": scanned, "mailbox": mailbox}
            self.save(data)
            self.log("read", added=count, pending=len(data["emails"]))
            return {"added": count, "revision": data["revision"], "emails": data["emails"]}

    @staticmethod
    def check_revision(data, expected):
        if data["revision"] != expected:
            raise ValueError("O JSON mudou. Volta a ler os pendentes antes de guardar.")

    def drafts(self, replies, expected_revision):
        with locked(self.folder):
            data = self.load()
            self.check_revision(data, expected_revision)
            entries = {e["id"]: e for e in data["emails"]}
            ids = [r["id"] for r in replies]
            if not ids or len(ids) != len(set(ids)):
                raise ValueError("Indica uma lista não vazia, sem IDs repetidos.")
            for reply in replies:
                if reply["id"] not in entries:
                    raise ValueError("Email desconhecido.")
                if entries[reply["id"]].get("reply_status") in ("sending", "uncertain"):
                    raise ValueError("Verifica primeiro no Gmail o envio com resultado incerto.")
                if not isinstance(reply["reply_text"], str) or len(reply["reply_text"]) > 100000:
                    raise ValueError("Resposta inválida ou demasiado longa.")
            for reply in replies:
                entries[reply["id"]].update(reply_text=reply["reply_text"], send_reply=False,
                                             reply_status="draft")
            data.pop("send_preview", None)
            self.save(data)
            self.log("drafts_saved", count=len(replies))
            return {"saved": len(replies), "revision": data["revision"]}

    @staticmethod
    def selected(data, ids):
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Seleciona IDs distintos.")
        entries = {e["id"]: e for e in data["emails"]}
        if any(key not in entries for key in ids):
            raise ValueError("Email desconhecido ou já enviado.")
        selected = [entries[key] for key in ids]
        if any(e.get("reply_status") in ("sending", "uncertain") for e in selected):
            raise ValueError("Envio incerto: verifica Enviados no Gmail antes de resolver.")
        return selected

    @staticmethod
    def snapshot(data, ids):
        return hashlib.sha256(json.dumps(
            [data["account"], [e for key in ids for e in data["emails"] if e["id"] == key]],
            sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def preview(self, ids):
        with locked(self.folder):
            data = self.load()
            entries = self.selected(data, ids)
            replies = []
            for item in entries:
                msg, recipient = build_reply(item, data["account"])
                replies.append({"id": item["id"], "to": recipient, "subject": str(msg["Subject"]),
                                "reply_text": item["reply_text"]})
            token = secrets.token_urlsafe(32)
            data["send_preview"] = {"token_hash": hashlib.sha256(token.encode()).hexdigest(),
                                    "ids": ids, "snapshot": self.snapshot(data, ids),
                                    "expires": time.time() + 900}
            self.save(data)
            return {"preview_token": token, "expires_in_seconds": 900, "replies": replies,
                    "instruction": "Mostra destinatários e respostas ao utilizador e pede confirmação explícita."}

    def send(self, preview_token, confirmed):
        if confirmed is not True:
            raise ValueError("É necessária confirmação explícita do utilizador após rever o lote.")
        with locked(self.folder):
            data = self.load()
            preview = data.get("send_preview", {})
            if (not secrets.compare_digest(preview.get("token_hash", ""), hashlib.sha256(preview_token.encode()).hexdigest())
                or preview.get("expires", 0) < time.time()):
                raise ValueError("Pré-visualização inválida ou expirada. Prepara novamente o envio.")
            ids = preview["ids"]
            if self.snapshot(data, ids) != preview["snapshot"]:
                raise ValueError("As respostas mudaram; é necessário rever novamente.")
            entries = self.selected(data, ids)
            # Validate everything before connecting or sending anything.
            messages = [(item, *build_reply(item, data["account"])) for item in entries]
            password = app_password(self.folder, data["account"])
            results = []
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
                smtp.login(data["account"], password)
                data.pop("send_preview", None)
                self.save(data)
                for item, msg, recipient in messages:
                    # Persist BEFORE SMTP. A crash must never cause an automatic retry.
                    item.update(reply_status="sending", reply_message_id=str(msg["Message-ID"]),
                                reply_last_attempt_at=now(), send_reply=False)
                    self.save(data)
                    try:
                        refused = smtp.send_message(msg)
                        if refused:
                            raise smtplib.SMTPRecipientsRefused(refused)
                    except smtplib.SMTPResponseException as exc:
                        item["reply_status"] = "error"
                        item["reply_error"] = f"SMTP {exc.smtp_code}"
                    except smtplib.SMTPRecipientsRefused:
                        item["reply_status"] = "error"
                        item["reply_error"] = "Destinatário recusado pelo SMTP."
                    except Exception:
                        item["reply_status"] = "uncertain"
                        item["reply_error"] = "Ligação interrompida; verifica Enviados no Gmail antes de repetir."
                    else:
                        data["replied_message_ids"].append(item["id"])
                        data["emails"].remove(item)
                        item["reply_status"] = "sent"
                    # A save failure propagates; do NOT rewrite it as a failed SMTP send.
                    self.save(data)
                    status = item["reply_status"]
                    results.append({"id": item["id"], "status": status})
                    self.log("send", message_id=item["id"], status=status)
                    if status == "uncertain":
                        break
            return {"results": results, "remaining": len(data["emails"])}

    def resolve(self, message_id, was_sent):
        """Local operator recovery only, after checking Gmail Sent."""
        with locked(self.folder):
            data = self.load()
            item = next((e for e in data["emails"] if e["id"] == message_id), None)
            if not item or item.get("reply_status") not in ("sending", "uncertain"):
                raise ValueError("Não existe esse envio incerto.")
            if was_sent:
                data["replied_message_ids"].append(item["id"])
                data["emails"].remove(item)
            else:
                item.update(reply_status="draft", send_reply=False)
            data.pop("send_preview", None)
            self.save(data)
            self.log("resolved", message_id=message_id, was_sent=was_sent)
