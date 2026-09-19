"""The calls (use cases) shared by the page, the MCP and the terminal commands. No AI SDK or API.

They take and return plain data that converts to JSON, and do not know who called them.
"""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets
import smtplib
import time
import os
from .ai import KNOWLEDGE_RULE, describe, instructions
from .configure import STARTER, example_profile
from .mail import build_reply, read_messages
from .rules import build_profile, check_profile, clean_property, prepare, route
from .secrets import app_password
from .store import locked, load_json, load_profiles, load_voice, save_json

VIEW_FIELDS = ("id", "kind", "date", "subject", "customer", "recipient", "blocked", "body_text", "body_truncated",
               "reply_text", "reply_status", "reply_error", "reply_message_id")
# Page field → (profile prompt, key), the same prompts the terminal setup asks for.
PROMPT_FIELDS = {"general": ("general", "text"), "first": ("first_interaction", "text"),
                 "first_template": ("first_interaction", "reply_template"), "second": ("second_interaction", "text"),
                 "knowledge": ("knowledge", "text")}


def write_private(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(text)


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

    def profiles(self):
        profiles = load_profiles(self.folder, self.config()["account"])
        if not profiles and (self.folder / "voice.json").exists():
            # voice.json marks a property instance: never fall back to importing the whole mailbox.
            raise ValueError("Esta pasta trabalha por imóveis (tem voice.json), mas não há nenhum "
                             "properties/<REF>/profile.json. Copia os perfis reais: não estão no Git.")
        return profiles

    def check(self):
        """Refuse to start with an incomplete setup: account, profiles and, with profiles, the voice."""
        if self.profiles():
            load_voice(self.folder)

    @staticmethod
    def pick(profiles, property_ref):
        """The queue an operation uses: the general one, or one property's (validated names only)."""
        if not profiles:
            if property_ref:
                raise ValueError("Esta instância não tem imóveis configurados.")
            return None
        if property_ref is None and len(profiles) == 1:
            return next(iter(profiles))
        if property_ref not in profiles:
            raise ValueError("Indica o imóvel em property_ref: " + ", ".join(profiles))
        return property_ref

    def queue_path(self, ref=None):
        return self.path if ref is None else self.folder / "properties" / ref / "queue.json"

    def load(self, ref=None):
        account = self.config()["account"]
        data = load_json(self.queue_path(ref), {"account": account, "created_at": now(),
                                               "revision": 0, "emails": [], "replied_message_ids": []})
        if data.get("account") != account:
            raise ValueError("A conta do JSON difere da configuração. Usa uma pasta por conta.")
        for item in data["emails"]:
            item["id"] = message_key(item)
        data.setdefault("revision", 0)
        data.setdefault("replied_message_ids", [])
        data.setdefault("dismissed_message_ids", [])
        if ref:
            data.setdefault("property", ref)
            data.setdefault("conversations", {})
        return data

    def save(self, data, ref=None):
        data["revision"] += 1
        data["updated_at"] = now()
        data.setdefault("stats", {})["emails_in_queue"] = len(data["emails"])
        save_json(self.queue_path(ref), data)

    def log(self, event, **fields):
        # No bodies, passwords, OAuth tokens, subjects or recipient addresses in logs.
        folder = self.folder / "logs"
        folder.mkdir(mode=0o700, exist_ok=True)
        import os
        fd = os.open(folder / "events.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as stream:
            stream.write(json.dumps({"at": now(), "event": event, **fields}) + "\n")

    @staticmethod
    def view(ref, profile, data, voice, added=None):
        """What the model gets for one property: pending emails, interaction number and instructions."""
        def customer(item):
            return ((item.get("recipient") or {}).get("email") or "").casefold()
        conversations = data["conversations"]
        counts = Counter(customer(item) for item in data["emails"])
        emails = []
        for item in data["emails"]:
            email = customer(item)
            warnings = list(item.get("warnings", []))
            if email and counts[email] > 1:
                warnings.append("Há outro email pendente deste cliente neste imóvel; evita respostas repetidas.")
            emails.append({key: item.get(key) for key in VIEW_FIELDS} | {
                "interaction": conversations.get(email, {}).get("stage", 0) + 1 if email else None,
                "warnings": warnings})
        result = {"property_ref": ref, "revision": data["revision"], "last_read_at": data.get("last_read_at"),
                  "instructions": instructions(profile, voice), "emails": emails}
        if added is not None:
            result["added"] = added
        return result

    def pending(self, property_ref=None):
        with locked(self.folder):
            profiles = self.profiles()
            if not profiles:
                self.pick(profiles, property_ref)
                data = self.load()
                return {"revision": data["revision"], "account": data["account"],
                        "emails": data["emails"], "last_read_at": data.get("last_read_at")}
            refs = [self.pick(profiles, property_ref)] if property_ref else list(profiles)
            voice = load_voice(self.folder)
            return {"account": self.config()["account"],
                    "properties": [self.view(ref, profiles[ref], self.load(ref), voice) for ref in refs]}

    def read(self):
        with locked(self.folder):
            cfg = self.config()
            profiles = self.profiles()
            refs = list(profiles) or [None]
            queues = {ref: self.load(ref) for ref in refs}
            start_at = now()
            start = datetime.now(timezone.utc).date() - timedelta(days=max(0, int(cfg.get("lookback_days", 2))))
            for data in queues.values():
                if data.get("last_read_at"):
                    # One-day overlap handles date boundaries; IDs remove duplicates.
                    start = min(start, datetime.fromisoformat(data["last_read_at"]).date() - timedelta(days=1))
            known = {ref: {message_key(e) for e in data["emails"]} | set(data["replied_message_ids"])
                     | set(data["dismissed_message_ids"]) for ref, data in queues.items()}
            seen = set().union(*known.values())

            def accept(item):
                # Decided on headers: known IDs and, with profiles, mail outside their families are skipped.
                return message_key(item) not in seen and (not profiles or route(item, profiles, queues)[1] is not None)

            messages, scanned, mailbox = read_messages(
                cfg["account"], app_password(self.folder, cfg["account"]),
                "" if profiles else cfg.get("subject_contains", ""), start.isoformat(),
                datetime.now(timezone.utc).date().isoformat(),
                mailbox=cfg.get("mailbox", "all"), incoming_only=bool(profiles) or cfg.get("incoming_only", True),
                accept=accept)
            added, ambiguous = dict.fromkeys(refs, 0), 0
            for item in messages:
                ref, kind, customer = route(item, profiles, queues) if profiles else (None, "general", None)
                if kind == "ambiguous":
                    ambiguous += 1
                if kind in (None, "ambiguous"):
                    continue
                key = message_key(item)
                if key in known[ref]:
                    continue
                if profiles:
                    item.update(prepare(item, kind, customer, profiles[ref], cfg["account"]), kind=kind)
                item.update(id=key, reply_text="", send_reply=False, reply_status="pending")
                queues[ref]["emails"].append(item)
                known[ref].add(key)
                added[ref] += 1
            for ref, data in queues.items():
                data["last_read_at"] = start_at
                data["stats"] = {"new_this_read": added[ref], "scanned": scanned, "mailbox": mailbox}
                self.save(data, ref)
            self.log("read", added=sum(added.values()), ambiguous=ambiguous,
                     pending=sum(len(data["emails"]) for data in queues.values()))
            if not profiles:
                data = queues[None]
                return {"added": added[None], "revision": data["revision"], "emails": data["emails"]}
            voice = load_voice(self.folder)
            return {"scanned": scanned, "ambiguous": ambiguous,
                    "properties": [self.view(ref, profiles[ref], queues[ref], voice, added[ref]) for ref in refs]}

    @staticmethod
    def check_revision(data, expected):
        if data["revision"] != expected:
            raise ValueError("O JSON mudou. Volta a ler os pendentes antes de guardar.")

    def drafts(self, replies, expected_revision, property_ref=None):
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
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
            self.save(data, ref)
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
    def check_recipients(entries, profile, account):
        # Checked again at preview and at send: the profile may have changed since READ.
        never = {a.casefold() for a in profile.get("reply", {}).get("never_reply_to", [])} | {account.casefold()}
        for item in entries:
            if item.get("blocked"):
                raise ValueError(f"Envio bloqueado ({item['id']}): {item['blocked']}")
            if ((item.get("recipient") or {}).get("email") or "").casefold() in never | {""}:
                raise ValueError(f"Destinatário proibido ou em falta ({item['id']}). Revê manualmente.")

    @staticmethod
    def advance(data, item):
        # The stage outlives the email in the queue; only address, IDs and dates are kept.
        conversation = data["conversations"].setdefault(
            item["recipient"]["email"].casefold(), {"stage": 0, "sent_message_ids": [], "thread_ids": []})
        conversation["stage"] += 1
        conversation["sent_message_ids"].append(item["reply_message_id"])
        if item.get("thread_id") and item["thread_id"] not in conversation["thread_ids"]:
            conversation["thread_ids"].append(item["thread_id"])
        conversation["last_sent_at"] = now()

    @staticmethod
    def snapshot(data, ids):
        return hashlib.sha256(json.dumps(
            [data["account"], [e for key in ids for e in data["emails"] if e["id"] == key]],
            sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def preview(self, ids, property_ref=None):
        with locked(self.folder):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            data = self.load(ref)
            entries = self.selected(data, ids)
            if ref:
                self.check_recipients(entries, profiles[ref], data["account"])
            replies = []
            for item in entries:
                msg, recipient = build_reply(item, data["account"])
                replies.append({"id": item["id"], "to": recipient, "subject": str(msg["Subject"]),
                                "reply_text": item["reply_text"], "warnings": item.get("warnings", [])})
            token = secrets.token_urlsafe(32)
            data["send_preview"] = {"token_hash": hashlib.sha256(token.encode()).hexdigest(),
                                    "ids": ids, "snapshot": self.snapshot(data, ids),
                                    "expires": time.time() + 900}
            self.save(data, ref)
            return {"preview_token": token, "expires_in_seconds": 900, "property_ref": ref, "replies": replies,
                    "instruction": "Mostra destinatários, respostas e warnings ao utilizador e pede confirmação explícita."}

    def send(self, preview_token, confirmed, property_ref=None):
        if confirmed is not True:
            raise ValueError("É necessária confirmação explícita do utilizador após rever o lote.")
        with locked(self.folder):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            data = self.load(ref)
            preview = data.get("send_preview", {})
            if (not secrets.compare_digest(preview.get("token_hash", ""), hashlib.sha256(preview_token.encode()).hexdigest())
                or preview.get("expires", 0) < time.time()):
                raise ValueError("Pré-visualização inválida ou expirada. Prepara novamente o envio.")
            ids = preview["ids"]
            if self.snapshot(data, ids) != preview["snapshot"]:
                raise ValueError("As respostas mudaram; é necessário rever novamente.")
            entries = self.selected(data, ids)
            if ref:
                self.check_recipients(entries, profiles[ref], data["account"])
            # Validate everything before connecting or sending anything.
            messages = [(item, *build_reply(item, data["account"])) for item in entries]
            password = app_password(self.folder, data["account"])
            results = []
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
                smtp.login(data["account"], password)
                data.pop("send_preview", None)
                self.save(data, ref)
                for item, msg, recipient in messages:
                    # Persist BEFORE SMTP. A crash must never cause an automatic retry.
                    item.update(reply_status="sending", reply_message_id=str(msg["Message-ID"]),
                                reply_last_attempt_at=now(), send_reply=False)
                    self.save(data, ref)
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
                        if ref:
                            self.advance(data, item)
                    # A save failure propagates; do NOT rewrite it as a failed SMTP send.
                    self.save(data, ref)
                    status = item["reply_status"]
                    results.append({"id": item["id"], "status": status})
                    self.log("send", message_id=item["id"], status=status)
                    if status == "uncertain":
                        break
            return {"results": results, "remaining": len(data["emails"])}

    def dismiss(self, ids, expected_revision, property_ref=None):
        """Leave the queue without a reply. Gmail is untouched; the ID is never imported again."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            self.check_revision(data, expected_revision)
            for item in self.selected(data, ids):
                data["emails"].remove(item)
                data["dismissed_message_ids"].append(item["id"])
            data.pop("send_preview", None)
            self.save(data, ref)
            self.log("dismissed", count=len(ids))
            return {"dismissed": len(ids), "revision": data["revision"]}

    def marked(self, property_ref=None):
        """Local SEND only: drafts marked with send_reply=true directly in the JSON."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            return ref, [e["id"] for e in self.load(ref)["emails"]
                         if e.get("send_reply") is True and str(e.get("reply_text", "")).strip()]

    def resolve(self, message_id, was_sent, property_ref=None):
        """Local operator recovery only, after checking Gmail Sent."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            item = next((e for e in data["emails"] if e["id"] == message_id), None)
            if not item or item.get("reply_status") not in ("sending", "uncertain"):
                raise ValueError("Não existe esse envio incerto.")
            if was_sent:
                data["replied_message_ids"].append(item["id"])
                data["emails"].remove(item)
                if ref:
                    self.advance(data, item)
            else:
                item.update(reply_status="draft", send_reply=False)
            data.pop("send_preview", None)
            self.save(data, ref)
            self.log("resolved", message_id=message_id, was_sent=was_sent)

    def settings(self):
        """Voice choices and property profiles for the local page; works while the voice is incomplete."""
        with locked(self.folder):
            account = self.config()["account"]
            style = load_json(self.folder / "voice.json", {}).get("style") or {}
            voice = {key: {"selected": (style.get(key) or {}).get("selected"),
                           "options": {name: describe(option)
                                       for name, option in ((style.get(key) or {}).get("options") or {}).items()}}
                     for key in ("greeting", "languages", "closing")}
            voice["signature"] = (style.get("signature") or {}).get("text") or ""
            properties = []
            for ref, profile in load_profiles(self.folder, account).items():
                prompts = profile.get("reply", {}).get("prompts", {})
                properties.append({"sender": profile["match"]["from_address_equals"],
                                   "prompts": {name: (prompts.get(key) or {}).get(field) or ""
                                               for name, (key, field) in PROMPT_FIELDS.items()},
                                   "knowledge_files": [part["file"] for part in profile["_knowledge"]],
                                   **{key: profile["property"].get(key) for key in (
                                       "reference", "listing_id", "listing_url", "advertiser", "description",
                                       "advertised_rent_eur")}})
            return {"account": account, "voice": voice, "properties": properties}

    def save_voice(self, choices):
        with locked(self.folder):
            path = self.folder / "voice.json"
            voice = load_json(path, None)
            if not voice:
                raise ValueError("Falta voice.json nesta pasta: corre o setup primeiro.")
            style = voice["style"]
            for key in ("greeting", "languages", "closing"):
                if choices.get(key) not in (style.get(key) or {}).get("options", {}):
                    raise ValueError(f"Opção inválida: {key}.")
                style[key].update(selected=choices[key], status="configured")
            signature = " ".join(str(choices.get("signature") or "").split())
            if not signature or len(signature) > 200:
                raise ValueError("A assinatura é obrigatória (até 200 caracteres).")
            style["signature"].update(text=signature, status="configured")
            save_json(path, voice)
            self.log("voice_saved")

    def save_property(self, fields):
        """Create or update a property from listing data; the facts go to its knowledge base."""
        fields = clean_property(fields)
        if not fields["reference"] or not fields["description"]:
            raise ValueError("Indica pelo menos a referência e a descrição do imóvel.")
        with locked(self.folder):
            account = self.config()["account"]
            profiles = load_profiles(self.folder, account)
            ref = fields["reference"]
            # A new property copies the owner's first profile (their prompts), else the published example.
            template = next(iter(profiles.values()), None) or example_profile(self.folder)
            profile = build_profile(fields, account, template, profiles.get(ref), date.today())
            check_profile(ref, profile, account)
            folder = self.folder / "properties" / ref
            save_json(folder / "profile.json", profile)
            knowledge = folder / "knowledge"
            if not knowledge.exists():
                knowledge.mkdir(mode=0o700)
                write_private(knowledge / "imovel.md", STARTER.format(ref=ref))
            if fields["facts"]:
                write_private(knowledge / "anuncio.md", "# Dados do anúncio\n\n<!-- Extraídos do anúncio pela página "
                              "local; confirma e corrige. Este ficheiro é substituído na próxima extração. -->\n\n"
                              + "\n".join(f"- {fact}" for fact in fields["facts"]) + "\n")
            self.log("property_saved", reference=ref)
            return {"reference": ref, "created": ref not in profiles}

    def save_prompts(self, ref, texts):
        with locked(self.folder):
            account = self.config()["account"]
            profiles = load_profiles(self.folder, account)
            if ref not in profiles:
                raise ValueError("Imóvel desconhecido.")
            profile = profiles[ref]
            profile.pop("_knowledge", None)  # runtime only, never written to profile.json
            values = {name: str(texts.get(name) or "").strip() for name in PROMPT_FIELDS}
            if any(len(value) > 10000 for value in values.values()):
                raise ValueError("Texto demasiado longo (máximo 10 000 caracteres).")
            if not values["general"]:
                raise ValueError("O prompt base do imóvel é obrigatório.")
            prompts = profile.setdefault("reply", {}).setdefault("prompts", {})
            for name, (key, field) in PROMPT_FIELDS.items():
                prompts.setdefault(key, {})[field] = values[name] or None
            prompts["knowledge"]["text"] = values["knowledge"] or KNOWLEDGE_RULE
            for key in ("general", "first_interaction", "second_interaction", "knowledge"):
                prompts[key]["status"] = "configured" if prompts[key].get("text") else "awaiting_owner"
            save_json(self.folder / "properties" / ref / "profile.json", profile)
            self.log("prompts_saved", reference=ref)
