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
from .rules import (KNOWLEDGE_FILE, SUBJECT_DEFAULT, VISIT_SLOT_DEFAULT, VISIT_STATES, build_profile, check_profile,
                    check_slot, check_window, clean_property, free_times, knowledge, photo_of, prepare, route,
                    subject_of)
from .secrets import app_password, has_app_password
from .store import (add_note, find_photo, knowledge_files, load_events, load_knowledge, load_visits, locked,
                    load_json, load_profiles, load_voice, property_folder, read_photo, save_json, save_text,
                    save_visits, write_photo)

VIEW_FIELDS = ("id", "kind", "date", "subject", "customer", "recipient", "blocked", "body_text", "body_truncated",
               "reply_text", "reply_status", "reply_error", "reply_message_id", "visit_window", "visit_slot",
               "visit_status")
# Page field → (profile prompt, key), the same prompts the terminal setup asks for.
PROMPT_FIELDS = {"general": ("general", "text"), "first": ("first_interaction", "text"),
                 "first_template": ("first_interaction", "reply_template"), "second": ("second_interaction", "text"),
                 "third": ("third_interaction", "text"), "fourth": ("fourth_interaction", "text"),
                 "knowledge": ("knowledge", "text")}


def write_private(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(text)


def now():
    return datetime.now(timezone.utc).isoformat()


def waited_hours(item):
    """Hours between the customer's email and now, or None when the email had no usable date."""
    try:
        arrived = datetime.fromisoformat(str(item.get("date") or ""))
    except ValueError:
        return None
    if arrived.tzinfo is None:
        arrived = arrived.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - arrived).total_seconds() / 3600, 1)


def message_key(item):
    for field in ("gmail_message_id", "message_id", "id"):
        if item.get(field):
            return str(item[field]).strip()
    raise ValueError("Email sem identificador estável.")


class MailService:
    """The calls of one data folder: read, drafts, preview, send, dismiss, resolve and the settings.

    Every call takes and returns plain data (it becomes JSON for the page and the MCP) and runs under the
    folder's lock. The safety rules live here, never in api.py or mcp.py: only the Reply-To, blocked emails
    never go out, the queue revision, and a preview token that a human must confirm before sending.
    """
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.path = self.folder / "queue.json"

    def config(self):
        """config.json, with a usable account; nothing starts without one."""
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
        """One queue (a property's, or the single one), with every field the older files may lack."""
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
        """Writes a queue atomically and bumps its revision, so a stale draft can never overwrite it."""
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
    def view(ref, profile, data, voice, added=None, visits=None):
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
            stage = conversations.get(email, {}).get("stage", 0)
            emails.append({key: item.get(key) for key in VIEW_FIELDS} | {
                "interaction": (3 if item.get("kind") == "visit_proposal" else stage + 1) if email else None,
                "warnings": warnings})
        result = {"property_ref": ref, "revision": data["revision"], "last_read_at": data.get("last_read_at"),
                  "instructions": instructions(profile, voice, visits), "emails": emails}
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
                    "properties": [self.view(ref, profiles[ref], self.load(ref), voice, visits=self.open_visits(ref, voice))
                                   for ref in refs]}

    def read(self, days=None):
        """Brings the new emails. days: how far back this read looks (default: lookback_days of config.json)."""
        if days is not None and (isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365):
            raise ValueError("Indica os dias para trás: um número de 1 a 365.")
        with locked(self.folder):
            cfg = self.config()
            profiles = self.profiles()
            refs = list(profiles) or [None]
            queues = {ref: self.load(ref) for ref in refs}
            start_at = now()
            back = days if days is not None else max(0, int(cfg.get("lookback_days", 7)))
            start = datetime.now(timezone.utc).date() - timedelta(days=back)
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
                    "properties": [self.view(ref, profiles[ref], queues[ref], voice, added[ref], self.open_visits(ref, voice))
                                   for ref in refs]}

    @staticmethod
    def check_revision(data, expected):
        if data["revision"] != expected:
            raise ValueError("O JSON mudou. Volta a ler os pendentes antes de guardar.")

    def drafts(self, replies, expected_revision, property_ref=None, visits=None):
        """Saves drafts in a batch; visits: the visit time or the visit status the assistant marked per email."""
        visits = visits or []
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            self.check_revision(data, expected_revision)
            entries = {e["id"]: e for e in data["emails"]}
            ids = [r["id"] for r in replies]
            if (not ids and not visits) or len(ids) != len(set(ids)):
                raise ValueError("Indica uma lista não vazia, sem IDs repetidos.")
            self.check_visits(ref, data, entries, visits)
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
            for visit in visits:
                item = entries[visit["id"]]
                if visit.get("visit_slot"):
                    item["visit_slot"] = visit["visit_slot"]
                if visit.get("visit_status"):
                    # What the customer said stands at once, even before our answer goes out.
                    item["visit_status"] = visit["visit_status"]
                    email = ((item.get("recipient") or {}).get("email") or "").casefold()
                    if email in data.get("conversations", {}):
                        data["conversations"][email]["visit"] = visit["visit_status"]
            data.pop("send_preview", None)
            self.save(data, ref)
            self.log("drafts_saved", count=len(replies), visits=len(visits))
            return {"saved": len(replies), "revision": data["revision"]}

    @staticmethod
    def selected(data, ids):
        """The chosen emails, refused whole if one is unknown, repeated or waiting for an uncertain send."""
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
        """After a successful send: the customer's conversation moves to the next interaction."""
        # The stage outlives the email in the queue. Kept: address, name, our last subject, IDs, dates and
        # the visit status; never a body. A visit proposal is always the 3rd interaction, whatever came before.
        conversation = data["conversations"].setdefault(
            item["recipient"]["email"].casefold(), {"stage": 0, "sent_message_ids": [], "thread_ids": []})
        stage = conversation["stage"] + 1
        conversation["stage"] = max(stage, 3) if item.get("kind") == "visit_proposal" else stage
        name = (item.get("recipient") or {}).get("name") or (item.get("customer") or {}).get("name")
        if name:
            conversation["name"] = name
        if item.get("reply_subject"):
            conversation["subject"] = item["reply_subject"]
        if item.get("visit_status"):
            conversation["visit"] = item["visit_status"]
        conversation["sent_message_ids"].append(item["reply_message_id"])
        if item.get("thread_id") and item["thread_id"] not in conversation["thread_ids"]:
            conversation["thread_ids"].append(item["thread_id"])
        conversation["last_sent_at"] = now()

    @staticmethod
    def snapshot(data, ids):
        return hashlib.sha256(json.dumps(
            [data["account"], [e for key in ids for e in data["emails"] if e["id"] == key]],
            sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def composer(self, profiles, ref, account):
        """How each reply is built: the shared voice gives the From name and the subject of a portal lead."""
        style = load_voice(self.folder).get("style", {}) if ref else {}
        name = (style.get("sender_name") or {}).get("text") or ""
        template = (style.get("reply_subject") or {}).get("text") or None

        def compose(item):
            subject = subject_of(item.get("kind"), template, profiles[ref]) if ref else None
            return build_reply(item, account, name, subject)
        return compose

    def preview(self, ids, property_ref=None):
        with locked(self.folder):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            data = self.load(ref)
            entries = self.selected(data, ids)
            if ref:
                self.check_recipients(entries, profiles[ref], data["account"])
            compose = self.composer(profiles, ref, data["account"])
            replies = []
            for item in entries:
                msg, recipient = compose(item)
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
            compose = self.composer(profiles, ref, data["account"])
            messages = [(item, *compose(item)) for item in entries]
            agenda = load_visits(self.folder, ref) if ref and any(item.get("visit_slot") for item in entries) else None
            if agenda is not None:
                slots = [item["visit_slot"] for item in entries if item.get("visit_slot")]
                if len(slots) != len(set(slots)) or {slot["at"] for slot in agenda["slots"]} & set(slots):
                    raise ValueError("Há horas de visita repetidas ou já marcadas neste lote: revê os rascunhos.")
            password = app_password(self.folder, data["account"])
            results = []
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
                smtp.login(data["account"], password)
                data.pop("send_preview", None)
                self.save(data, ref)
                for item, msg, recipient in messages:
                    # Persist BEFORE SMTP. A crash must never cause an automatic retry.
                    item.update(reply_status="sending", reply_message_id=str(msg["Message-ID"]),
                                reply_subject=str(msg["Subject"]), reply_last_attempt_at=now(), send_reply=False)
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
                        if agenda is not None and item.get("visit_slot"):
                            agenda["slots"].append({"at": item["visit_slot"], "customer": recipient.casefold(),
                                                    "name": (item.get("recipient") or {}).get("name") or "",
                                                    "booked_at": now()})
                            save_visits(self.folder, ref, agenda)
                    # A save failure propagates; do NOT rewrite it as a failed SMTP send.
                    self.save(data, ref)
                    status = item["reply_status"]
                    results.append({"id": item["id"], "status": status})
                    # How long the customer waited, for the dashboard; no address, subject or text is logged.
                    self.log("send", message_id=item["id"], status=status,
                             waited_hours=None if item.get("kind") == "visit_proposal" else waited_hours(item))
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

    @staticmethod
    def visit_rules(voice):
        """The voice's visit settings: every how many minutes, and how long a rental or a sale visit takes."""
        visits = (voice.get("style") or {}).get("visits") or {}
        return {"slot": int(visits.get("slot_minutes") or VISIT_SLOT_DEFAULT),
                "rental": visits.get("rental") or "", "sale": visits.get("sale") or ""}

    def open_visits(self, ref, voice):
        """The windows still to come and their free times, for the assistant's instructions."""
        if not ref:
            return None
        rules = self.visit_rules(voice)
        agenda = load_visits(self.folder, ref)
        booked = {slot["at"] for slot in agenda["slots"]}
        today = date.today().isoformat()
        return {**rules, "windows": [{**window, "free": free_times(window, rules["slot"], booked)}
                                     for window in agenda["windows"] if window["day"] >= today]}

    def check_visits(self, ref, data, entries, visits):
        """The visit marks of a pasted answer: known emails, a known status, and a free time on the agenda."""
        for visit in visits:
            if visit.get("id") not in entries:
                raise ValueError("Email desconhecido.")
            if visit.get("visit_status") and visit["visit_status"] not in VISIT_STATES:
                raise ValueError("Estado de visita inválido.")
        slots = [visit for visit in visits if visit.get("visit_slot")]
        if not slots:
            return
        if not ref:
            raise ValueError("As visitas só existem com imóveis.")
        slot = self.visit_rules(load_voice(self.folder))["slot"]
        agenda = load_visits(self.folder, ref)
        today = date.today().isoformat()
        windows = [window for window in agenda["windows"] if window["day"] >= today]
        marked = {visit["id"] for visit in slots}
        # Booked times, and times already in other drafts of this queue, are taken.
        taken = {booked["at"] for booked in agenda["slots"]}
        taken |= {item["visit_slot"] for item in data["emails"] if item.get("visit_slot") and item["id"] not in marked}
        for visit in slots:
            check_slot(visit["visit_slot"], windows, slot, taken)
            taken.add(visit["visit_slot"])

    def candidates(self, ref, data):
        """Everyone this property has written to, and whether the visit proposal goes to them now."""
        agenda = load_visits(self.folder, ref)
        today = date.today().isoformat()
        booked = {slot["customer"] for slot in agenda["slots"] if slot["at"][:10] >= today}
        waiting = {((item.get("recipient") or {}).get("email") or "").casefold() for item in data["emails"]}
        found = []
        for email, conversation in sorted(data.get("conversations", {}).items()):
            if email in booked:
                state, reason = "booked", "já tem visita marcada"
            elif email in waiting:
                state, reason = "pending", "tem um email por responder"
            elif conversation.get("visit") in VISIT_STATES:
                state, reason = conversation["visit"], VISIT_STATES[conversation["visit"]]
            else:
                state, reason = "ok", ""
            found.append({"email": email, "name": conversation.get("name") or "", "state": state, "reason": reason,
                          "stage": conversation.get("stage", 0)})
        return found

    def visit_candidates(self, property_ref=None):
        """The customers a visit proposal can go to; those who declined come unticked in the page."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            if not ref:
                raise ValueError("As visitas só existem com imóveis.")
            return {"property_ref": ref, "customers": self.candidates(ref, self.load(ref))}

    def propose_visits(self, property_ref, day, start, end, emails):
        """The owner's visit window, and one draft per chosen customer, in the customer's own conversation.

        The drafts are written by the assistant like any other (3rd interaction) and sent after the preview.
        Customers with an email still to answer, or a visit already booked, never get a second email."""
        window = check_window(day, start, end)
        if window["day"] < date.today().isoformat():
            raise ValueError("Esse dia já passou.")
        chosen = list(dict.fromkeys(str(email or "").strip().casefold() for email in emails or []))
        if not chosen or "" in chosen:
            raise ValueError("Escolhe pelo menos um cliente.")
        with locked(self.folder):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            if not ref:
                raise ValueError("As visitas só existem com imóveis.")
            data = self.load(ref)
            customers = {customer["email"]: customer for customer in self.candidates(ref, data)}
            for email in chosen:
                if email not in customers:
                    raise ValueError(f"{email} não é cliente deste imóvel.")
                if customers[email]["state"] in ("pending", "booked"):
                    raise ValueError(f"{email}: {customers[email]['reason']}.")
            window["id"] = f"{window['day']}_{window['start']}_{window['end']}".replace(":", "")
            agenda = load_visits(self.folder, ref)
            if all(existing["id"] != window["id"] for existing in agenda["windows"]):
                agenda["windows"].append({**window, "created_at": now()})
            style = load_voice(self.folder).get("style", {})
            first_subject = subject_of("lead", (style.get("reply_subject") or {}).get("text") or None, profiles[ref])
            created = 0
            for email in chosen:
                key = f"visita-{window['id']}-{hashlib.sha256(email.encode()).hexdigest()[:8]}"
                if any(item["id"] == key for item in data["emails"]):
                    continue
                conversation = data["conversations"][email]
                sent = conversation.get("sent_message_ids") or []
                name = conversation.get("name") or ""
                # It answers our last email, so it lands in the customer's own conversation. The key also goes
                # in gmail_message_id, because load() takes the id from there before message_id.
                data["emails"].append({
                    "id": key, "gmail_message_id": key, "kind": "visit_proposal", "date": now(),
                    "subject": conversation.get("subject") or first_subject or "",
                    "message_id": sent[-1] if sent else "", "references": " ".join(sent[:-1]),
                    "thread_id": (conversation.get("thread_ids") or [""])[-1],
                    "recipient": {"name": name, "email": email},
                    "customer": {"name": name or None, "email": email, "phone": None, "message": None},
                    "blocked": None, "warnings": [], "visit_window": dict(window),
                    "reply_text": "", "send_reply": False, "reply_status": "pending"})
                created += 1
            save_visits(self.folder, ref, agenda)
            self.save(data, ref)
            self.log("visits_proposed", reference=ref, created=created)
            return {"property_ref": ref, "created": created, "window": window}

    def voice_ready(self):
        try:
            load_voice(self.folder)
            return True
        except ValueError:
            return False

    def metrics(self):
        """Numbers for the dashboard. Nothing that identifies a customer leaves this call."""
        with locked(self.folder):
            account = self.config()["account"]
            profiles = load_profiles(self.folder, account)
            refs = list(profiles) or [None]
            first = datetime.now(timezone.utc).date() - timedelta(days=13)
            days = [(first + timedelta(days=n)).isoformat() for n in range(14)]
            requests, totals, properties, last_read = Counter(), Counter(), [], None
            for ref in refs:
                data = self.load(ref)
                emails = data["emails"]
                status = Counter(item.get("reply_status") or "pending" for item in emails)
                blocked = sum(1 for item in emails if item.get("blocked"))
                conversations = data.get("conversations", {})
                answered = sum(conversation.get("stage", 0) for conversation in conversations.values())
                for item in emails:
                    requests[str(item.get("date") or "")[:10]] += 1
                totals.update(pending=len(emails), drafts=status["draft"], blocked=blocked, answered=answered,
                              customers=len(conversations),
                              attention=status["uncertain"] + status["error"] + status["sending"])
                last_read = max([stamp for stamp in (last_read, data.get("last_read_at")) if stamp], default=None)
                listing = profiles[ref]["property"] if ref else {}
                properties.append({"property_ref": ref, "pending": len(emails), "drafts": status["draft"],
                                   "blocked": blocked, "answered": answered, "customers": len(conversations),
                                   "last_read_at": data.get("last_read_at"), "description": listing.get("description"),
                                   "listing_url": listing.get("listing_url"),
                                   "advertised_rent_eur": listing.get("advertised_rent_eur"),
                                   "photo": bool(ref) and find_photo(self.folder, ref) is not None})
            sent, waited = Counter(), []
            for event in load_events(self.folder):
                if event.get("event") == "send" and event.get("status") == "sent":
                    sent[str(event.get("at") or "")[:10]] += 1
                    if isinstance(event.get("waited_hours"), (int, float)):
                        waited.append(event["waited_hours"])
            return {"account": account, "last_read_at": last_read, "properties": properties,
                    "totals": {key: totals[key] for key in
                               ("pending", "drafts", "blocked", "attention", "answered", "customers")},
                    "by_day": [{"day": day, "requests": requests.get(day, 0), "sent": sent.get(day, 0)}
                               for day in days],
                    "reply_hours": round(sum(waited) / len(waited), 1) if waited else None,
                    "setup": {"account": bool(account), "app_password": has_app_password(self.folder, account),
                              "voice": self.voice_ready(), "properties": len(profiles)}}

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
            voice["sender_name"] = (style.get("sender_name") or {}).get("text") or ""
            voice["reply_subject"] = (style.get("reply_subject") or {}).get("text") or SUBJECT_DEFAULT
            voice["application_instructions"] = load_json(self.folder / "voice.json", {}).get("application_instructions") or ""
            visits = style.get("visits") or {}
            voice["visits"] = {"slot_minutes": visits.get("slot_minutes") or VISIT_SLOT_DEFAULT,
                               "rental": visits.get("rental") or "", "sale": visits.get("sale") or ""}
            today = date.today().isoformat()
            properties = []
            for ref, profile in load_profiles(self.folder, account).items():
                prompts = profile.get("reply", {}).get("prompts", {})
                properties.append({"sender": profile["match"]["from_address_equals"],
                                   "prompts": {name: (prompts.get(key) or {}).get(field) or ""
                                               for name, (key, field) in PROMPT_FIELDS.items()},
                                   "knowledge_files": [part["file"] for part in profile["_knowledge"]],
                                   "photo": find_photo(self.folder, ref) is not None,
                                   "visits": {"windows": [window for window in load_visits(self.folder, ref)["windows"]
                                                          if window["day"] >= today],
                                              "slots": sorted((slot for slot in load_visits(self.folder, ref)["slots"]
                                                               if slot["at"][:10] >= today), key=lambda s: s["at"])},
                                   **{key: profile["property"].get(key) for key in (
                                       "reference", "listing_id", "listing_url", "advertiser", "description",
                                       "advertised_rent_eur")}})
            return {"account": account, "voice": voice, "properties": properties,
                    "lookback_days": int(self.config().get("lookback_days", 7))}

    def save_photo(self, ref, image):
        """The property's photo for the page: the owner's own file, kept in its private folder."""
        kind, data = photo_of(image)
        with locked(self.folder):
            if ref not in load_profiles(self.folder, self.config()["account"]):
                raise ValueError("Imóvel desconhecido.")
            write_photo(self.folder, ref, kind, data)
            self.log("photo_saved", reference=ref)

    def photo(self, ref):
        """(bytes, media type) of a property's photo, or None."""
        return read_photo(self.folder, ref)

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
            # Both go into the headers: one line only, never a newline the page could smuggle in.
            name = " ".join(str(choices.get("sender_name") or "").split())
            if len(name) > 100:
                raise ValueError("O nome do remetente é demasiado longo (até 100 caracteres).")
            style.setdefault("sender_name", {}).update(text=name, status="configured" if name else "not_configured")
            subject = " ".join(str(choices.get("reply_subject") or "").split()) or SUBJECT_DEFAULT
            if len(subject) > 200:
                raise ValueError("O assunto é demasiado longo (até 200 caracteres).")
            style.setdefault("reply_subject", {}).update(text=subject, status="configured")
            if "application_instructions" in choices:
                behaviour = str(choices.get("application_instructions") or "").strip()
                if len(behaviour) > 3000:
                    raise ValueError("O comportamento geral é demasiado longo (até 3000 caracteres).")
                voice["application_instructions"] = behaviour
            visits = choices.get("visits")
            if visits is not None:
                if not isinstance(visits, dict):
                    raise ValueError("Definições de visitas inválidas.")
                try:
                    slot = int(visits.get("slot_minutes"))
                except (TypeError, ValueError):
                    raise ValueError("Indica de quantos em quantos minutos se marcam as visitas.") from None
                if not 10 <= slot <= 180:
                    raise ValueError("As visitas marcam-se de 10 a 180 minutos.")
                texts = {key: " ".join(str(visits.get(key) or "").split()) for key in ("rental", "sale")}
                if any(len(value) > 80 for value in texts.values()):
                    raise ValueError("A duração das visitas é demasiado longa (até 80 caracteres).")
                style["visits"] = {"slot_minutes": slot, **texts, "status": "configured"}
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

    def knowledge(self, property_ref=None):
        """What the assistant knows, exactly as it gets it: the property's base and the agency's know-how."""
        with locked(self.folder):
            profiles = self.profiles()
            # Without a property (several of them), only the agency's know-how: that is its own editor.
            ref = self.pick(profiles, property_ref) if property_ref or len(profiles) <= 1 else None
            base = property_folder(self.folder, ref) if ref else None
            files = lambda folder: [{"file": name, "text": text} for name, text in knowledge_files(folder)]
            return {"property_ref": ref, "agency": load_knowledge(self.folder),
                    "property": load_knowledge(base) if ref else [],
                    # The files as the owner wrote them, comments included, for editing in the page.
                    "files": {"agency": files(self.folder), "property": files(base) if ref else []}}

    def save_knowledge(self, property_ref, file, text, scope="property"):
        """Writes one knowledge (RAG) file, whole. An empty text leaves the file empty, so it no longer counts."""
        file, text = str(file or "").strip(), str(text or "").replace("\r\n", "\n")
        if not KNOWLEDGE_FILE.fullmatch(file):
            raise ValueError("O nome do ficheiro só pode ter letras, algarismos, _ e -, e acabar em .md.")
        if scope not in ("property", "agency"):
            raise ValueError("Escolhe onde guardar: neste imóvel ou para todos.")
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref) if scope == "property" else None
            if scope == "property" and not ref:
                raise ValueError("Esta pasta não tem imóveis.")
            base = property_folder(self.folder, ref) if ref else self.folder
            # The whole base must stay within its limit, with this file as it will be.
            knowledge([(name, body) for name, body in knowledge_files(base) if name != file] + [(file, text)])
            save_text(base / "knowledge" / file, text if text.endswith("\n") or not text else text + "\n")
            self.log("knowledge_saved", scope=scope, reference=ref)
            return {"scope": scope, "property_ref": ref, "file": file}

    def add_note(self, property_ref, text, scope="property"):
        """A fact the owner adds while reviewing replies; the next prompt already carries it."""
        text = " ".join(str(text or "").split())
        if not text or len(text) > 500:
            raise ValueError("Escreve a informação numa ou duas frases (até 500 caracteres).")
        if scope not in ("property", "agency"):
            raise ValueError("Escolhe onde guardar: neste imóvel ou para todos.")
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref) if scope == "property" else None
            if scope == "property" and not ref:
                raise ValueError("Esta pasta não tem imóveis.")
            add_note(property_folder(self.folder, ref) if ref else self.folder, text, date.today())
            self.log("note_added", scope=scope, reference=ref)
            return {"scope": scope, "property_ref": ref}

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
            for key in ("general", "first_interaction", "second_interaction", "third_interaction",
                        "fourth_interaction", "knowledge"):
                prompts[key]["status"] = "configured" if prompts[key].get("text") else "awaiting_owner"
            save_json(self.folder / "properties" / ref / "profile.json", profile)
            self.log("prompts_saved", reference=ref)
