"""The calls (use cases) shared by the page, the MCP and the terminal commands. No AI SDK, and the only
API is OpenAI's, used the same way SMTP already was here: a plain HTTP call, optional, behind a key the
owner supplies — never a requirement to draft or send a reply.

They take and return plain data that converts to JSON, and do not know who called them.
"""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import smtplib
import time
import os
from .ai import (AFTER_VISIT_RULE, AFTER_VISIT_TEMPLATE, KNOWLEDGE_RULE, agenda_prompt, describe, instructions,
                 parse_agenda, parse_survey, visit_analysis_prompt)
from .configure import STARTER, example_profile
from .mail import build_digest, build_reply, read_messages
from .openai_client import MODEL_DEFAULT, complete, estimate_cost_usd
from .rules import (DAY, EMAIL, KNOWLEDGE_FILE, RGPD_STATES, SUBJECT_DEFAULT, VISIT_SLOT_DEFAULT, VISIT_STATES,
                    FICHA_FIELDS, build_profile, check_profile, ficha_summary, merge_ficha, check_slot, check_window, clean_property, consent_yes, free_times,
                    knowledge, photo_of, prepare, property_active, route, subject_of, QUOTE, addresses)
from .secrets import app_password, has_app_password, has_openai_api_key, openai_api_key
from .store import (CONTACT_FIELDS, add_contacts, add_note, find_photo, knowledge_files, load_contacts, load_digest,
                    load_events, load_knowledge, load_panel, load_visits, locked, load_json, load_profiles, load_voice,
                    property_folder, read_photo, save_contacts, save_digest, save_json, save_panel, save_text,
                    save_visits, write_photo)

CONTACT_SOURCE = "Idealista"  # today's only portal; see README for the family of emails it accepts.
# Sent automatically or by a one-click button, in the customer's conversation, but never counted as one
# of the four interactions and never resetting the clock the 2/4-day reminders are measured from.
AUX_KINDS = {"reminder", "consent_request", "visits_closed", "addition", "visit_thanks"}  # "addition": «Escrever mais»; "visit_thanks": after the visit
PROGRAM_KINDS = AUX_KINDS | {"visit_proposal"}  # drafts the program creates; not an email a customer sent
REMINDER_HOURS = {"2d": 48, "4d": 96}
HISTORY_LIMIT = 20  # turns kept per conversation, oldest dropped first; also what the prompt gets
# Dashboard chart: period in days → days per bar (90 days per day would be 90 unreadable bars).
CHART_PERIODS = {3: 1, 7: 1, 14: 1, 30: 1, 90: 7}

VIEW_FIELDS = ("id", "kind", "date", "subject", "customer", "recipient", "blocked", "body_text", "body_truncated",
               "reply_text", "reply_status", "reply_error", "reply_message_id", "visit_window", "visit_slot",
               "visit_status", "reminder", "closing", "consent_suggested", "consent_confirmed", "history", "merged",
               "merged_ids", "visit_done")
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


IGNORE_KINDS = ("black", "grey")
# Each property's API "fuel tank": a spending cap the owner fills by hand on the property's panel
# (properties/<REF>/painel.json), since that is where it is best watched. OpenAI's cost is in US$, estimated
# from tokens; for this assistant 1 € = 1 US$, by the owner's choice (24/09): no rate, no conversion shown.
# data/api_fuel.json was the one shared tank before: a property not filled since keeps its size and fill time.
FUEL_DEFAULT_EUR = 5.0
FUEL_RESERVE = 0.15  # below this share of the tank, the reserve lamp lights up
# Each property's reply-time limit, in hours: the top (H) of its temperature dial, set on the page like the
# tank's size. Past it, the dial is overheated. 24 h until the owner sets another one.
REPLY_HOURS_MAX_DEFAULT = 24
REPLY_HOURS_MAX_RANGE = (1, 720)
# The petrol the visits take, per property: the agency-to-property distance (one way) and the car's
# consumption. A day of visits is one round trip, however many visits it holds.
DISTANCE_KM_RANGE = (0, 1000)
L_PER_100KM_DEFAULT = 7.0
L_PER_100KM_RANGE = (1, 40)


def number_in(value, bounds, message, digits=1):
    """A number from the page (text or number) inside bounds, or a ValueError with the owner's message."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(message) from None
    if not bounds[0] <= number <= bounds[1]:  # NaN fails this too
        raise ValueError(message)
    return int(number) if number.is_integer() else round(number, digits)


def stored_number(value, bounds, default):
    """A number read back from a JSON file: anything unexpected there reads as the default."""
    valid = isinstance(value, (int, float)) and not isinstance(value, bool) and bounds[0] <= value <= bounds[1]
    return value if valid else default


def ignore_kind(conversation):
    """Which ignore list: stored since 24/09; before that, a reason meant the customer opted out."""
    kind = conversation.get("ignored_kind")
    return kind if kind in IGNORE_KINDS else "grey" if conversation.get("ignored_reason") else "black"


def shut_out(conversation):
    """Blacklist: nothing of theirs comes in again. Greylist (26/09): we stop writing first — no reminders, rounds,
    consent or closing — but what they write still comes in, and can be answered."""
    return bool(conversation.get("ignored")) and ignore_kind(conversation) == "black"


def was_proposed(conversation, email, proposed):
    """A visit was already proposed to them: by a round (proposed: everyone ever invited or booked), or as the
    conversation shows (offered, accepted, another date asked, or checked after a visit)."""
    return bool(email in proposed or conversation.get("visit_proposed") or conversation.get("visit_offered")
                or conversation.get("visit_accepted") or conversation.get("visit") == "outra_data"
                or conversation.get("visit_check"))


def waited_hours(item):
    """Hours between the customer's email and now, or None when the email had no usable date."""
    try:
        arrived = datetime.fromisoformat(str(item.get("date") or ""))
    except ValueError:
        return None
    if arrived.tzinfo is None:
        arrived = arrived.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - arrived).total_seconds() / 3600, 1)


def contact_day(item):
    """The email's own date for primeiro_contacto, or today when it has none usable."""
    day = str(item.get("date") or "")[:10]
    return day if DAY.fullmatch(day) else date.today().isoformat()


def message_key(item):
    for field in ("gmail_message_id", "message_id", "id"):
        if item.get(field):
            return str(item[field]).strip()
    raise ValueError("Email sem identificador estável.")


def recipient_email(item):
    return ((item.get("recipient") or {}).get("email") or "").casefold()


def aware(value):
    """An ISO date as an aware datetime (UTC when it has no offset), or None."""
    try:
        moment = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def insert_turn(history, turn):
    """Puts a turn found later (a reply written in Gmail) where it belongs in time: before the first turn that
    is later — by its exact time when kept, else by its day (a turn with no time counts as earlier that day)."""
    stamp = turn.get("ts") or turn.get("at") or ""
    position = next((index for index, other in enumerate(history)
                     if (other["ts"] > stamp if other.get("ts") else (other.get("at") or "") > stamp[:10])), len(history))
    history.insert(position, turn)


def plain_subject(value):
    """The subject without Re:/Fwd:/Enc: prefixes, for comparing a reply with what it answers."""
    subject = " ".join(str(value or "").split())
    while True:
        shorter = re.sub(r"^(re|res|fw|fwd|enc|rv)\s*:\s*", "", subject, flags=re.I)
        if shorter == subject:
            return subject.casefold()
        subject = shorter


def own_text(body):
    """What the owner wrote in a reply, without the quoted email under it (and Gmail's «Em … escreveu:» line)."""
    lines = str(body or "").splitlines()
    cut = next((i for i, line in enumerate(lines) if QUOTE.match(line.strip())), len(lines))
    lines = lines[:cut]
    while lines and not lines[-1].strip():
        lines.pop()
    # Gmail wraps a long «Em …, Nome <email> escreveu:» over two or three lines: drop it from its start.
    if lines and re.search(r"(escreveu|wrote):?$", lines[-1].strip()):
        start = next((i for i in range(len(lines) - 1, max(len(lines) - 4, -1), -1)
                      if re.match(r"^(Em|On|No dia) ", lines[i].strip())), None)
        lines = lines[:start] if start is not None else lines
    return "\n".join(lines).strip()


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
        # Still arranging a time: while a window the customer was invited to is open and they have no visit
        # booked, every reply after the proposal is the 4th interaction (book it, or offer the time left),
        # never a 5th without a prompt. A window from before the invitees were kept (α.19.0) invites everyone.
        windows = (visits or {}).get("windows") or []
        invited = {(person.get("email") or "").casefold() for window in windows for person in window.get("recipients") or []}
        everyone = any("recipients" not in window for window in windows)
        booked = set((visits or {}).get("booked") or ())
        proposed = set((visits or {}).get("proposed") or ())
        emails = []
        for item in data["emails"]:
            email = customer(item)
            warnings = list(item.get("warnings", []))
            if email and counts[email] > 1:
                warnings.append("Há outro email pendente deste cliente neste imóvel; evita respostas repetidas.")
            conversation = conversations.get(email, {})
            interaction = 3 if item.get("kind") == "visit_proposal" else conversation.get("stage", 0) + 1
            if item.get("kind") == "addition":
                interaction = conversation.get("stage", 0)  # one more email within the step already reached
            if (item.get("answered_directly") or {}).get("interaction"):
                interaction = item["answered_directly"]["interaction"]  # answered in Gmail: it keeps its step
            # Qualification (26/09): until a visit is proposed, every email of theirs is the 2nd interaction —
            # ask only what their file still lacks — never the 3rd (the proposal) just by counting emails.
            qualifying = bool(ref and email and item.get("kind") not in PROGRAM_KINDS
                              and not item.get("answered_directly") and not was_proposed(conversation, email, proposed))
            if qualifying and interaction > 2:
                interaction = 2
            limit = qualifying and conversation.get("stage", 0) >= 4  # the 1st reply and three questions already
            ficha = conversation.get("ficha") or item.get("ficha")
            missing = ficha_summary(ficha)["falta"] if ref and email else []
            if missing and not qualifying and (item.get("kind") == "visit_proposal" or interaction == 4):
                # 26/09: an incomplete file never holds back the proposal or the booking; the customer is
                # reminded, and the owner decides whether to confirm.
                warnings.append("Ficha incompleta (falta: " + ", ".join(FICHA_FIELDS[key] for key in missing).lower()
                                + "): a IA lembra o cliente; decides tu se confirmas a visita.")
            if limit:
                warnings.append("Já pedimos informação três vezes sem a ficha ficar completa: a IA não volta a "
                                "perguntar. Decide se lhe propões visita na mesma.")
            if (interaction > 4 and (everyone or email in invited) and email not in booked
                    and conversation.get("visit") != "nao_quer"):
                interaction = 4
            emails.append({key: item.get(key) for key in VIEW_FIELDS} | {
                "interaction": interaction if email else None, "warnings": warnings,
                "ficha": ficha, "ficha_summary": ficha_summary(ficha) if ref else None, "qualifying_limit": limit,
                # The whole conversation as it stands now — also what came after this email (a reply
                # written in Gmail, one more email) — for «Email completo»; the prompt keeps «history».
                "conversation": list(conversation.get("history") or [])})
        # «Enviados ficam na fila» (25/09): every active customer already answered — by the page or in Gmail —
        # stays in view as a sent card until a visit is booked, they decline or are ignored, visits close, or
        # the owner takes the card out (it comes back when that conversation moves again).
        busy = {customer(item) for item in data["emails"]}
        active = []
        if ref and visits is not None and not visits.get("closed"):
            for email, conversation in sorted(conversations.items(), key=lambda pair: pair[1].get("last_sent_at") or "",
                                              reverse=True):
                removed = conversation.get("queue_removed_at")
                if (conversation.get("ignored") or not conversation.get("stage") or email in busy or email in booked
                        or conversation.get("visit") == "nao_quer" or (removed and removed == conversation.get("last_sent_at"))):
                    continue
                active.append({"email": email, "name": conversation.get("name") or "", "stage": conversation.get("stage", 0),
                               "last_sent_at": conversation.get("last_sent_at"), "last_text": conversation.get("last_text") or "",
                               "visit": conversation.get("visit"),
                               "visit_accepted": (conversation.get("visit_accepted") or {}).get("at"),
                               "history": list(conversation.get("history") or [])})
        result = {"property_ref": ref, "revision": data["revision"], "last_read_at": data.get("last_read_at"),
                  "instructions": instructions(profile, voice, visits), "emails": emails, "active": active,
                  "inactive": not property_active(profile)}
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
            closed_refs = {ref for ref in refs if ref and load_visits(self.folder, ref).get("closed_at")}
            voice_ok = None
            if profiles:
                try:
                    voice_ok = load_voice(self.folder)
                except ValueError:
                    pass  # incomplete voice: the read still runs, just without auto-drafts this time
            queues = {ref: self.load(ref) for ref in refs}
            start_at = now()
            back = days if days is not None else max(0, int(cfg.get("lookback_days", 7)))
            start = datetime.now(timezone.utc).date() - timedelta(days=back)
            for data in queues.values():
                if data.get("last_read_at"):
                    # One-day overlap handles date boundaries; IDs remove duplicates.
                    start = min(start, datetime.fromisoformat(data["last_read_at"]).date() - timedelta(days=1))
            known = {ref: {message_key(e) for e in data["emails"]} | {merged for e in data["emails"] for merged in e.get("merged_ids", [])}
                     | set(data["replied_message_ids"]) | set(data["dismissed_message_ids"]) for ref, data in queues.items()}
            seen = set().union(*known.values())

            def accept(item):
                # Decided on headers: known IDs and, with profiles, mail outside their families are skipped.
                return message_key(item) not in seen and (not profiles or route(item, profiles, queues)[1] is not None)

            # The owner's own replies, written straight from Gmail: to someone we know, or in a thread we know.
            # Never one this page sent: its Message-ID is in the conversation already.
            outgoing = [] if profiles else None
            talks = [conversation for data in queues.values() for conversation in data.get("conversations", {}).values()]
            ours = {sent for conversation in talks for sent in conversation.get("sent_message_ids", [])}
            people = ({email for data in queues.values() for email in data.get("conversations", {})}
                      | {recipient_email(item) for data in queues.values() for item in data["emails"]}) - {""}
            threads = ({item.get("thread_id") for data in queues.values() for item in data["emails"]}
                       | {thread for conversation in talks for thread in conversation.get("thread_ids", [])}) - {None, ""}

            def accept_outgoing(item):
                recipients = {a.casefold() for a in addresses((item.get("to") or []) + (item.get("cc") or []))}
                return item.get("message_id") not in ours and bool(recipients & people or item.get("thread_id") in threads)

            messages, scanned, mailbox = read_messages(
                cfg["account"], app_password(self.folder, cfg["account"]),
                "" if profiles else cfg.get("subject_contains", ""), start.isoformat(),
                datetime.now(timezone.utc).date().isoformat(),
                mailbox=cfg.get("mailbox", "all"), incoming_only=bool(profiles) or cfg.get("incoming_only", True),
                accept=accept, outgoing=outgoing, accept_outgoing=accept_outgoing)
            added, ambiguous, contacts, received = dict.fromkeys(refs, 0), 0, [], {}
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
                    email = str(item["customer"].get("email") or "").strip().casefold()
                    if email and shut_out(queues[ref]["conversations"].get(email) or {}):
                        # On the blacklist for this property: never re-enters, whatever they write.
                        continue
                    if email and (queues[ref]["conversations"].get(email) or {}).get("ignored"):
                        item.setdefault("warnings", []).append(
                            "Cliente na greylist: não recebe envios nossos, mas escreveu. Responde só se fizer sentido.")
                    if email:
                        contacts.append({"email": email, "nome": item["customer"].get("name") or "",
                                         "telefone": item["customer"].get("phone") or "",
                                         "primeiro_contacto": contact_day(item), "imovel": ref,
                                         "fonte": CONTACT_SOURCE})
                    # Known by their email already, whether this message is a direct reply (follow_up) or
                    # another portal notice (lead) from someone we have written to before either way.
                    conversation = queues[ref]["conversations"].get(email) if email else None
                    if conversation is not None and (conversation.get("visit_check") or {}).get("thanks_sent_at"):
                        # An answer to the after-visit email: the survey and the visit sheet, kept on the customer.
                        survey = parse_survey(item["customer"].get("message") or item.get("body_text"))
                        if survey:
                            conversation["visit_survey"] = {**survey, "at": item.get("date") or now()}
                            item.setdefault("warnings", []).append(
                                "Resposta ao inquérito pós-visita registada (vê-a na Agenda, na visita deste cliente).")
                    if conversation is not None:
                        # A snapshot of everything before this message: shown in "Email completo" and sent
                        # in the prompt, so the assistant (ChatGPT or the API) sees the whole exchange.
                        item["history"] = list(conversation.get("history") or [])
                        self.append_history(conversation, "cliente", item["customer"].get("message"),
                                            contact_day(item), item.get("date"))
                    else:
                        item["history"] = []
                item.update(id=key, reply_text="", send_reply=False, reply_status="pending")
                if profiles and ref in closed_refs and not item.get("blocked") and voice_ok:
                    closing = ((voice_ok.get("style") or {}).get("visits_closed") or {}).get("text") or ""
                    if closing:
                        item.update(reply_text=closing, reply_status="draft", closing=True)
                elif profiles and kind == "follow_up":
                    conversation = queues[ref].get("conversations", {}).get(customer, {})
                    if (conversation.get("consent_asked") and not conversation.get("consent")
                            and consent_yes(item["customer"].get("message"))):
                        item["consent_suggested"] = True
                queues[ref]["emails"].append(item)
                known[ref].add(key)
                added[ref] += 1
                received[key] = contact_day(item)
            # After the customers' emails, so a direct reply can answer one that arrived in this same read.
            direct = self.record_direct_replies(queues, outgoing) if profiles else Counter()
            if profiles:
                for data in queues.values():
                    self.merge_pending(data)
            add_contacts(self.folder, contacts)
            for ref, data in queues.items():
                data["last_read_at"] = start_at
                data["stats"] = {"new_this_read": added[ref], "scanned": scanned, "mailbox": mailbox,
                                 "direct_replies": direct[ref]}
                if ref and voice_ok:
                    self.schedule_reminders(ref, data, voice_ok)
                self.save(data, ref)
            if profiles:
                self.prepare_digest(profiles, queues)
            # received: message ID → the day the customer's email arrived, so the dashboard still counts it
            # after it is answered or dismissed and leaves the queue. IDs and dates only, never an address.
            self.log("read", added=sum(added.values()), ambiguous=ambiguous, direct=sum(direct.values()),
                     pending=sum(len(data["emails"]) for data in queues.values()), received=received)
            if not profiles:
                data = queues[None]
                return {"added": added[None], "revision": data["revision"], "emails": data["emails"]}
            voice = load_voice(self.folder)
            return {"scanned": scanned, "ambiguous": ambiguous, "direct": sum(direct.values()),
                    "properties": [self.view(ref, profiles[ref], queues[ref], voice, added[ref], self.open_visits(ref, voice))
                                   for ref in refs]}

    @staticmethod
    def merge_pending(data):
        """Several emails from one customer in the queue become one card: one reply answers them all (25/09).

        The base is the oldest email still unanswered (its id, and the customer's wait for the dashboard),
        else the oldest; it takes the others' messages, oldest first, and answers the newest (In-Reply-To,
        thread, subject). Emails already answered in Gmail join too, as context: with anything still
        unanswered, the card is a new step. A draft written before the other messages goes back to review.
        Reminders, proposals, additions and blocked emails are never merged. Returns how many were merged.
        """
        groups = {}
        for item in data["emails"]:
            email = recipient_email(item)
            if (email and item.get("kind") not in PROGRAM_KINDS and not item.get("blocked")
                    and item.get("reply_status") in ("pending", "draft")):
                groups.setdefault(email, []).append(item)
        merged = 0
        oldest = datetime.min.replace(tzinfo=timezone.utc)
        for items in groups.values():
            if len(items) < 2:
                continue
            items.sort(key=lambda item: aware(item.get("date")) or oldest)
            open_items = [item for item in items if not item.get("answered_directly")]
            base, newest = (open_items or items)[0], items[-1]
            parts = []
            for item in items:
                parts += item.get("merged") or [{"id": item["id"], "date": item.get("date"),
                                                 "message": (item.get("customer") or {}).get("message") or item.get("body_text") or "",
                                                 "answered": (item.get("answered_directly") or {}).get("at")}]
            parts.sort(key=lambda part: aware(part.get("date")) or oldest)
            drafted = next((item.get("reply_text") for item in [base] + items if (item.get("reply_text") or "").strip()), "")
            warnings = [warning for item in items for warning in item.get("warnings", [])
                        if "diretamente no Gmail" not in warning and "revê-o antes de enviar" not in warning]

            def stamp(part):
                moment = aware(part.get("date"))
                return f"{moment.astimezone():%d/%m %H:%M}" if moment else "?"
            answered = [part for part in parts if part.get("answered")]
            if answered and open_items:
                warnings.append("Já respondeste no Gmail à(s) mensagem(ns) de " + ", ".join(stamp(part) for part in answered)
                                + ": responde agora ao que veio depois.")
            if drafted:
                warnings.append("Havia um rascunho escrito antes de chegarem as outras mensagens deste cliente: revê-o antes de enviar.")
            base.update({
                "merged": parts, "merged_ids": sorted({part["id"] for part in parts} - {base["id"]}),
                "customer": {**(base.get("customer") or {}), "message": "\n\n".join(
                    f"[{stamp(part)}{' · já respondida no Gmail' if part.get('answered') else ''}]\n{part['message']}".strip()
                    for part in parts)},
                "kind": newest.get("kind"), "subject": newest.get("subject") or base.get("subject"),
                "message_id": newest.get("message_id") or base.get("message_id"),
                "references": newest.get("references") or base.get("references"),
                "in_reply_to": newest.get("in_reply_to") or base.get("in_reply_to"),
                "thread_id": newest.get("thread_id") or base.get("thread_id"),
                "warnings": list(dict.fromkeys(warnings)), "reply_text": drafted,
                "reply_status": "pending" if drafted else base.get("reply_status", "pending")})
            if open_items:
                base.pop("answered_directly", None)
            else:
                base["answered_directly"] = max((item["answered_directly"] for item in items), key=lambda mark: mark.get("at") or "")
            gone = {id(item) for item in items if item is not base}
            data["emails"] = [item for item in data["emails"] if id(item) not in gone]
            merged += len(gone)
        return merged

    def record_direct_replies(self, queues, outgoing):
        """The replies the owner wrote straight from Gmail, found at READ in All Mail (or in Sent).

        Each is tied to one customer of one property: by the pending emails it answers (the same Gmail thread,
        or sent to their author), else by a conversation it went to; the subject settles a customer known in
        two properties, and one still unclear is left alone. Nothing leaves the queue (the owner may still add
        something): the customer's emails from before it are marked answered in Gmail, keep the step they had
        and warn the owner; that step is spent once, by the reply in Gmail. What the owner wrote joins the
        history of the conversation and of every email of that customer in the queue, so the next prompt reads
        it. Counted like a send, with the customer's wait.
        """
        recorded = Counter()
        ours = {sent for data in queues.values() for conversation in data["conversations"].values()
                for sent in conversation.get("sent_message_ids", [])}
        dated = [(aware(message.get("date")), message) for message in outgoing or []]
        for sent_at, message in sorted((pair for pair in dated if pair[0]), key=lambda pair: pair[0]):
            key = message.get("message_id")
            if not key or key in ours:
                continue
            recipients = {a.casefold() for a in addresses((message.get("to") or []) + (message.get("cc") or []))}
            thread = message.get("thread_id") or None

            def answers(item):
                arrived = aware(item.get("date"))
                return (item.get("kind") not in PROGRAM_KINDS and bool(recipient_email(item))
                        and item.get("reply_status") not in ("sending", "uncertain")
                        and (arrived is None or arrived <= sent_at))

            pairs = {(ref, recipient_email(item)) for ref, data in queues.items() for item in data["emails"]
                     if answers(item) and ((thread and item.get("thread_id") == thread)
                                           or recipient_email(item) in recipients)}
            if not pairs:
                pairs = {(ref, email) for ref, data in queues.items()
                         for email, conversation in data["conversations"].items()
                         if email in recipients or (thread and thread in conversation.get("thread_ids", []))}
            if len(pairs) > 1:
                subject = plain_subject(message.get("subject"))
                same = {(ref, email) for ref, email in pairs if subject and subject in (
                    {plain_subject(item.get("subject")) for item in queues[ref]["emails"] if recipient_email(item) == email}
                    | {plain_subject((queues[ref]["conversations"].get(email) or {}).get("subject"))})}
                pairs = same or pairs
            if len(pairs) != 1:
                continue
            [(ref, email)] = pairs
            data = queues[ref]
            if shut_out(data["conversations"].get(email) or {}):
                continue
            created = email not in data["conversations"]
            conversation = data["conversations"].setdefault(email, {"stage": 0, "sent_message_ids": [], "thread_ids": []})
            mine = [item for item in data["emails"] if recipient_email(item) == email and item.get("kind") not in PROGRAM_KINDS]
            if created:
                # A first email answered straight in Gmail: the conversation starts with what the customer wrote.
                for item in sorted(mine, key=lambda item: aware(item.get("date")) or sent_at):
                    self.append_history(conversation, "cliente", (item.get("customer") or {}).get("message"),
                                        contact_day(item), item.get("date"))
            # Nothing leaves the queue: the owner may still add something from the page, or take it out.
            answered = [item for item in mine if answers(item) and not item.get("answered_directly")]
            local = sent_at.astimezone()
            for item in answered:
                item["answered_directly"] = {"at": sent_at.astimezone(timezone.utc).isoformat(),
                                             "interaction": conversation.get("stage", 0) + 1}
                item.setdefault("warnings", []).append(
                    f"Já respondeste a este email diretamente no Gmail em {local:%d/%m} às {local:%H:%M}. "
                    "Envia outro só se quiseres acrescentar algo; senão, retira-o da fila.")
            if answered:
                # The reply written in Gmail is that step of the conversation.
                conversation["stage"] = conversation.get("stage", 0) + 1
                name = next(((item.get("recipient") or {}).get("name") or (item.get("customer") or {}).get("name")
                             for item in answered
                             if (item.get("recipient") or {}).get("name") or (item.get("customer") or {}).get("name")), "")
                if name and not conversation.get("name"):
                    conversation["name"] = name
            conversation.setdefault("sent_message_ids", []).append(key)
            if thread and thread not in conversation.setdefault("thread_ids", []):
                conversation["thread_ids"].append(thread)
            if not conversation.get("subject") and message.get("subject"):
                conversation["subject"] = message["subject"]
            text = own_text(message.get("body_text"))
            if text:
                conversation["last_text"] = text
                turn = {"who": "nos", "text": text[:4000], "at": sent_at.date().isoformat(),
                        "ts": sent_at.astimezone(timezone.utc).isoformat()}
                for holder in [conversation] + mine:
                    history = holder.setdefault("history", [])
                    insert_turn(history, dict(turn))
                    del history[:-HISTORY_LIMIT]
            last = aware(conversation.get("last_sent_at"))
            if last is None or sent_at > last:
                conversation["last_sent_at"] = sent_at.astimezone(timezone.utc).isoformat()
            ours.add(key)
            recorded[ref] += 1
            if answered:
                first = min((aware(item.get("date")) for item in answered if aware(item.get("date"))), default=None)
                self.log("send", message_id=answered[0]["id"], status="sent", kind="direct", reference=ref,
                         at=sent_at.astimezone(timezone.utc).isoformat(),
                         waited_hours=round((sent_at - first).total_seconds() / 3600, 1) if first else None)
        return recorded

    @staticmethod
    def check_revision(data, expected):
        if data["revision"] != expected:
            raise ValueError("O JSON mudou. Volta a ler os pendentes antes de guardar.")

    def drafts(self, replies, expected_revision, property_ref=None, visits=None, fichas=None):
        """Saves drafts in a batch; visits: the visit time or the visit status the assistant marked per email;
        fichas: the customer's file as the assistant updated it, kept at once (like a visit status)."""
        visits, fichas = visits or [], fichas or []
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            self.check_revision(data, expected_revision)
            entries = {e["id"]: e for e in data["emails"]}
            ids = [r["id"] for r in replies]
            if (not ids and not visits and not fichas) or len(ids) != len(set(ids)):
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
            for entry in fichas:
                item = entries.get(entry["id"])
                if not item or not ref:
                    continue
                email = ((item.get("recipient") or {}).get("email") or "").casefold()
                conversation = data.get("conversations", {}).get(email)
                item["ficha"] = {**merge_ficha((conversation or {}).get("ficha") or item.get("ficha"), entry["ficha"]),
                                 "at": now()}
                if conversation is not None:
                    conversation["ficha"] = item["ficha"]  # a new customer's is kept on their email until it is sent
            data.pop("send_preview", None)
            self.save(data, ref)
            self.log("drafts_saved", count=len(replies), visits=len(visits), fichas=len(fichas), reference=ref)
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
    def append_history(conversation, who, text, day, moment=None):
        """One turn of the conversation. moment (an ISO date-time) keeps same-day turns in their real order:
        a reply written in Gmail at 10:00 and the customer's email at 12:00 are both «today»."""
        if not text:
            return
        history = conversation.setdefault("history", [])
        turn = {"who": who, "text": text[:4000], "at": day}
        stamp = aware(moment) if moment else None
        if stamp:
            turn["ts"] = stamp.astimezone(timezone.utc).isoformat()
        history.append(turn)
        del history[:-HISTORY_LIMIT]

    @classmethod
    def advance(cls, data, item):
        """After a successful send: the customer's conversation moves to the next interaction.

        A reminder, a consent request or a visits-closed notice never counts as an interaction and never
        resets last_sent_at: the 2/4-day reminders keep measuring from the last real exchange.
        """
        # The stage outlives the email in the queue. Kept: address, name, our last subject, IDs, dates,
        # the last text sent (so a reminder can quote it), the visit status, and the last HISTORY_LIMIT
        # turns of the conversation (ours and the customer's), for context in the next prompt.
        conversation = data["conversations"].setdefault(
            item["recipient"]["email"].casefold(), {"stage": 0, "sent_message_ids": [], "thread_ids": []})
        # An email the owner already answered in Gmail spent its step then: one more email to it is an addition.
        aux = item.get("kind") in AUX_KINDS or bool(item.get("answered_directly"))
        if not aux:
            stage = conversation["stage"] + 1
            conversation["stage"] = max(stage, 3) if item.get("kind") == "visit_proposal" else stage
        if item.get("kind") == "visit_proposal":
            conversation["visit_proposed"] = True  # the qualification is over for them
        if item.get("ficha") and (conversation.get("ficha") or {}).get("at", "") <= item["ficha"].get("at", ""):
            conversation["ficha"] = item["ficha"]
        if item.get("kind") == "reminder" and item.get("reminder"):
            conversation.setdefault("reminders_sent", []).append(item["reminder"])
        name = (item.get("recipient") or {}).get("name") or (item.get("customer") or {}).get("name")
        if name:
            conversation["name"] = name
        if item.get("reply_subject"):
            conversation["subject"] = item["reply_subject"]
        if item.get("visit_status"):
            conversation["visit"] = item["visit_status"]
        if item.get("visit_slot"):
            conversation.pop("visit_accepted", None)  # booked now: no longer just accepted or offered
            conversation.pop("visit_offered", None)
        conversation["sent_message_ids"].append(item["reply_message_id"])
        if item.get("thread_id") and item["thread_id"] not in conversation["thread_ids"]:
            conversation["thread_ids"].append(item["thread_id"])
        if item.get("reply_text"):
            conversation["last_text"] = item["reply_text"]
            cls.append_history(conversation, "nos", item["reply_text"], now()[:10], now())
        if not aux or item.get("kind") in ("addition", "visit_thanks"):
            conversation["last_sent_at"] = now()
        if item.get("kind") == "visit_thanks":
            conversation.setdefault("visit_check", {})["thanks_sent_at"] = now()

    @staticmethod
    def aux_item(key, kind, email, conversation, text, **extra):
        """A program-prepared draft in an existing conversation: reminder, consent request or closing notice.

        It answers our last message to this customer (Re:, In-Reply-To), never a body the customer sent.
        """
        sent = conversation.get("sent_message_ids") or []
        return {"id": key, "gmail_message_id": key, "kind": kind, "date": now(),
               "subject": conversation.get("subject") or "", "message_id": sent[-1] if sent else "",
               "references": " ".join(sent[:-1]), "thread_id": (conversation.get("thread_ids") or [""])[-1],
               "recipient": {"name": conversation.get("name") or "", "email": email},
               "customer": {"name": conversation.get("name") or None, "email": email, "phone": None, "message": None},
               "blocked": None, "warnings": [], "reply_text": text, "send_reply": False, "reply_status": "draft",
               **extra}

    def schedule_reminders(self, ref, data, voice):
        """One draft per customer at 2 and at 4 days without an answer, capped at two, in order.

        Stops for a customer who answered (a pending email from them), whose reminder was dismissed, or
        once visits are closed. The phrase comes from the voice; the body under it is the last text sent.
        """
        if load_visits(self.folder, ref).get("closed_at"):
            return 0
        phrases = (voice.get("style", {}).get("reminders") or {})
        text = {key: (phrases.get(key) or {}).get("text") or "" for key in ("day2", "day4")}
        if not text["day2"] and not text["day4"]:
            return 0
        waiting = {((item.get("recipient") or {}).get("email") or "").casefold() for item in data["emails"]}
        already = {(((item.get("recipient") or {}).get("email") or "").casefold(), item.get("reminder"))
                  for item in data["emails"] if item.get("kind") == "reminder"}
        created = 0
        for email, conversation in data.get("conversations", {}).items():
            if (email in waiting or conversation.get("reminders_stopped") or conversation.get("ignored")
                    or not conversation.get("last_sent_at")):
                continue
            sent = set(conversation.get("reminders_sent") or [])
            hours = (datetime.now(timezone.utc)
                    - datetime.fromisoformat(conversation["last_sent_at"])).total_seconds() / 3600
            if "2d" not in sent and text["day2"] and hours >= REMINDER_HOURS["2d"]:
                threshold = "2d"
            elif "2d" in sent and "4d" not in sent and text["day4"] and hours >= REMINDER_HOURS["4d"]:
                threshold = "4d"
            else:
                continue
            if (email, threshold) in already:
                continue
            phrase = text["day2"] if threshold == "2d" else text["day4"]
            body = f"{phrase}\n\n{conversation['last_text']}" if conversation.get("last_text") else phrase
            key = f"lembrete-{threshold}-{hashlib.sha256(email.encode()).hexdigest()[:8]}"
            data["emails"].append(self.aux_item(key, "reminder", email, conversation, body, reminder=threshold))
            created += 1
        return created

    def digest_recipient(self):
        """The address that gets the daily status digest, from voice.json; leniently, not the full voice."""
        style = load_json(self.folder / "voice.json", {}).get("style") or {}
        return (style.get("digest_recipient") or {}).get("text") or ""

    @staticmethod
    def digest_text(profiles, queues, today):
        """One property per block: conversations, pending count, and who still needs a reply prepared."""
        lines = [f"Ponto de situação, {today}", ""]
        totals = Counter()
        for ref, profile in profiles.items():
            data = queues[ref]
            emails = data["emails"]
            conversations = data.get("conversations", {})
            drafted = sum(1 for item in emails if item.get("reply_status") == "draft")
            awaiting = [item for item in emails if item.get("reply_status") not in ("draft", "sent")]
            lines.append(f"{ref} — {profile['property'].get('description') or ref}")
            lines.append(f"- {len(conversations)} conversas; {len(emails)} pendentes na fila "
                         f"({drafted} com rascunho pronto, {len(awaiting)} por preparar).")
            if awaiting:
                names = ", ".join((item.get("customer") or {}).get("name")
                                  or (item.get("recipient") or {}).get("name") or "sem nome" for item in awaiting)
                lines.append(f"- Por preparar: {names}.")
            lines.append("")
            totals.update(conversas=len(conversations), pendentes=len(emails), por_preparar=len(awaiting))
        lines.append(f"No total: {totals['conversas']} conversas, {totals['pendentes']} pendentes, "
                     f"{totals['por_preparar']} por preparar.")
        return "\n".join(lines)

    def prepare_digest(self, profiles, queues):
        """Once a day, after a READ: today's status, as a draft only. Never sent without a click."""
        if not self.digest_recipient():
            return
        today = date.today().isoformat()
        existing = load_digest(self.folder)
        if existing and existing.get("date") == today:
            return
        save_digest(self.folder, {"date": today, "reply_text": self.digest_text(profiles, queues, today),
                                  "reply_status": "draft", "reply_error": None, "created_at": now(), "sent_at": None})

    def digest_view(self):
        with locked(self.folder):
            return load_digest(self.folder)

    def save_digest_text(self, text):
        text = str(text or "")
        if len(text) > 20000:
            raise ValueError("Texto demasiado longo.")
        with locked(self.folder):
            digest = load_digest(self.folder)
            if not digest:
                raise ValueError("Ainda não há ponto de situação preparado.")
            digest["reply_text"] = text
            save_digest(self.folder, digest)
            return digest

    def send_digest(self, confirmed):
        if confirmed is not True:
            raise ValueError("É necessária confirmação explícita do utilizador após rever o texto.")
        with locked(self.folder):
            digest = load_digest(self.folder)
            if not digest or digest.get("reply_status") not in ("draft", "error", "uncertain"):
                raise ValueError("Não há ponto de situação por enviar.")
            recipient = self.digest_recipient()
            if not EMAIL.fullmatch(recipient):
                raise ValueError("Configura um destinatário válido em Voz e estilo.")
            cfg = self.config()
            msg = build_digest(cfg["account"], recipient, f"Ponto de situação — {digest['date']}", digest["reply_text"])
            password = app_password(self.folder, cfg["account"])
            digest.update(reply_status="sending", reply_error=None)
            save_digest(self.folder, digest)
            try:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
                    smtp.login(cfg["account"], password)
                    refused = smtp.send_message(msg)
                    if refused:
                        raise smtplib.SMTPRecipientsRefused(refused)
            except smtplib.SMTPResponseException as exc:
                digest.update(reply_status="error", reply_error=f"SMTP {exc.smtp_code}")
            except smtplib.SMTPRecipientsRefused:
                digest.update(reply_status="error", reply_error="Destinatário recusado pelo SMTP.")
            except Exception:
                digest.update(reply_status="uncertain",
                              reply_error="Ligação interrompida; verifica Enviados no Gmail antes de repetir.")
            else:
                digest.update(reply_status="sent", sent_at=now())
            save_digest(self.folder, digest)
            self.log("digest_send", status=digest["reply_status"])
            return {"status": digest["reply_status"]}

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
            if ref:  # a blocked email can never go out: say that before asking for its draft
                self.check_recipients(entries, profiles[ref], data["account"])
            missing = [item for item in entries if not str(item.get("reply_text") or "").strip()]
            if missing:
                names = ", ".join((item.get("customer") or {}).get("name") or (item.get("recipient") or {}).get("name")
                                  or "sem nome" for item in missing)
                raise ValueError(f"{len(missing)} email(s) selecionado(s) ainda sem rascunho ({names}). Prepara-os "
                                 "nos passos 02 e 03, ou escreve o rascunho no próprio email e guarda-o, antes de "
                                 "pré-visualizar.")
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
                        data["replied_message_ids"].extend([item["id"], *item.get("merged_ids", [])])
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
                    # Program-made emails (visit proposal, reminder, closing, consent) answer no customer email:
                    # no waiting time, so they never skew the average or count as a request received.
                    self.log("send", message_id=item["id"], status=status, kind=item.get("kind"), reference=ref,
                             waited_hours=None if item.get("kind") in PROGRAM_KINDS or item.get("answered_directly")
                             else waited_hours(item))
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
                data["dismissed_message_ids"].extend([item["id"], *item.get("merged_ids", [])])
                if item.get("kind") == "reminder":
                    # The owner chose not to send this reminder: no more are prepared for this customer.
                    email = ((item.get("recipient") or {}).get("email") or "").casefold()
                    conversation = data.get("conversations", {}).get(email)
                    if conversation is not None:
                        conversation["reminders_stopped"] = True
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
                data["replied_message_ids"].extend([item["id"], *item.get("merged_ids", [])])
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
        """The windows still to come and their free times, for the assistant's instructions, and who is booked."""
        if not ref:
            return None
        rules = self.visit_rules(voice)
        agenda = load_visits(self.folder, ref)
        booked = {slot["at"] for slot in agenda["slots"]}
        today = date.today().isoformat()
        return {**rules, "windows": [{**window, "free": free_times(window, rules["slot"], booked)}
                                     for window in agenda["windows"] if window["day"] >= today],
                "booked": sorted({slot["customer"] for slot in agenda["slots"] if slot["at"][:10] >= today}),
                "proposed": sorted(self.proposed_to(agenda)),
                "closed": bool(agenda.get("closed_at"))}

    @staticmethod
    def proposed_to(agenda):
        """Everyone a visit was ever proposed to on this property's agenda: invited by a round, or booked."""
        return ({(person.get("email") or "").casefold() for window in agenda["windows"]
                 for person in window.get("recipients") or []} | {slot["customer"] for slot in agenda["slots"]}) - {""}

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
            if conversation.get("ignored"):
                # On the ignore list: never a visit candidate, never counted as active anywhere else
                # that reuses this list (round proposals, the analysis prompt, "Clientes ativos").
                continue
            if email in booked:
                state, reason = "booked", "já tem visita marcada"
            elif email in waiting:
                state, reason = "pending", "tem um email por responder"
            elif conversation.get("visit") in VISIT_STATES:
                state, reason = conversation["visit"], VISIT_STATES[conversation["visit"]]
            else:
                state, reason = "ok", ""
            found.append({"email": email, "name": conversation.get("name") or "", "state": state, "reason": reason,
                          "stage": conversation.get("stage", 0), "ficha": ficha_summary(conversation.get("ficha"))})
        return found

    def visit_candidates(self, property_ref=None):
        """The customers a visit proposal can go to; those who declined come unticked in the page."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            if not ref:
                raise ValueError("As visitas só existem com imóveis.")
            if load_visits(self.folder, ref).get("closed_at"):
                raise ValueError("Este imóvel já tem as visitas fechadas.")
            return {"property_ref": ref, "customers": self.candidates(ref, self.load(ref))}

    def visit_round_summary(self, property_ref=None, window_id=None):
        """Who a visit round went to, and where each one stands now: booked (and when), declined, or still
        waiting to reply. Defaults to the most recently created window with recipients."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            if not ref:
                raise ValueError("As visitas só existem com imóveis.")
            agenda = load_visits(self.folder, ref)
            windows = [w for w in agenda["windows"] if w.get("recipients")]
            if not windows:
                return {"property_ref": ref, "window": None, "recipients": []}
            window = next((w for w in windows if w["id"] == window_id), None) if window_id else None
            if window is None:
                window = max(windows, key=lambda w: w.get("created_at") or "")
            data = self.load(ref)
            states = {c["email"]: c for c in self.candidates(ref, data)}
            booked_at = {slot["customer"]: slot["at"] for slot in agenda["slots"]}
            recipients = []
            for person in window["recipients"]:
                info = states.get(person["email"], {})
                state = info.get("state", "ok")
                recipients.append({"email": person["email"], "name": person.get("name") or info.get("name") or "",
                                   "state": state, "reason": info.get("reason", ""),
                                   "visit_at": booked_at.get(person["email"]) if state == "booked" else None})
            return {"property_ref": ref, "window": {key: window[key] for key in ("day", "start", "end", "created_at")},
                    "recipients": recipients}

    def visit_analysis_prompt(self, property_ref=None):
        """Read-only prompt: what active clients have said, for the owner to read (via ChatGPT or the API)
        before choosing a visit window. Never parsed back; nothing here is saved as a draft."""
        with locked(self.folder):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            if not ref:
                raise ValueError("A análise só existe com imóveis.")
            data = self.load(ref)
            return visit_analysis_prompt(profiles[ref], self.candidates(ref, data), data.get("conversations", {}))

    def api_fuel(self, ref=None, events=None):
        """How much of a property's API tank is left: its size less what that property spent since its last
        fill (1 € = 1 US$). A property never filled keeps the old shared tank (data/api_fuel.json), with its
        own spending; with neither, no limit, as before tanks existed. Spent is an estimate, like the cost.
        ref None: the folder without properties, whose tank is data/api_fuel.json and counts every call."""
        tank = (load_panel(self.folder, ref) if ref else {}).get("tank") or load_json(self.folder / "api_fuel.json", None)
        if not tank:
            return {"configured": False, "capacity_eur": FUEL_DEFAULT_EUR, "spent_eur": 0, "remaining_eur": None,
                    "reserve": False, "empty": False, "filled_at": None}
        capacity, since = tank["capacity_eur"], tank["filled_at"]
        # Same ISO format for both (now()), so comparing the strings compares the moments.
        spent = sum(event.get("cost_usd", 0) for event in (events if events is not None else load_events(self.folder, limit=100000))
                    if event.get("event") == "openai_usage" and str(event.get("at") or "") >= since
                    and (ref is None or event.get("reference") == ref))
        remaining = round(capacity - spent, 4)
        return {"configured": True, "capacity_eur": capacity, "spent_eur": round(spent, 4), "remaining_eur": remaining,
                "reserve": remaining < capacity * FUEL_RESERVE, "empty": remaining <= 0, "filled_at": since}

    def fill_fuel(self, property_ref=None, capacity_eur=None):
        """Fills a property's tank: from now on the API may spend up to capacity_eur there again (estimated)."""
        capacity = number_in(FUEL_DEFAULT_EUR if capacity_eur in (None, "") else capacity_eur, (0.5, 1000),
                             "O depósito vai de 0,50 € a 1000 €.", digits=2)
        tank = {"capacity_eur": capacity, "filled_at": now()}
        with locked(self.folder):
            ref = self.pick(load_profiles(self.folder, self.config()["account"]), property_ref)
            if ref:
                panel = load_panel(self.folder, ref)
                panel["tank"] = tank
                save_panel(self.folder, ref, panel)
            else:
                save_json(self.folder / "api_fuel.json", tank)
            self.log("fuel_filled", reference=ref, capacity_eur=tank["capacity_eur"])
        return self.api_fuel(ref)

    def panel(self, ref):
        """How a property's instrument panel reads: its reply-time limit (the H of the temperature dial), and
        the distance to it and the car's consumption, for the petrol its visits take (no distance: unknown)."""
        stored = load_panel(self.folder, ref) if ref else {}
        return {"reply_hours_max": stored_number(stored.get("reply_hours_max"), REPLY_HOURS_MAX_RANGE, REPLY_HOURS_MAX_DEFAULT),
                "distance_km": stored_number(stored.get("distance_km"), DISTANCE_KM_RANGE, None),
                "l_per_100km": stored_number(stored.get("l_per_100km"), L_PER_100KM_RANGE, L_PER_100KM_DEFAULT)}

    def save_panel(self, property_ref, reply_hours_max=None, distance_km=None, l_per_100km=None):
        """Sets what the page sends of a property's panel: the reply-time limit, in hours (past it, the
        temperature dial is overheated), the one-way distance to it in km, the car's litres per 100 km."""
        low, high = REPLY_HOURS_MAX_RANGE
        checks = {"reply_hours_max": (reply_hours_max, REPLY_HOURS_MAX_RANGE,
                                      f"O tempo máximo de resposta vai de {low} a {high} horas."),
                  "distance_km": (distance_km, DISTANCE_KM_RANGE, "A distância ao imóvel vai de 0 a 1000 km."),
                  "l_per_100km": (l_per_100km, L_PER_100KM_RANGE, "O consumo do carro vai de 1 a 40 L/100 km.")}
        values = {key: number_in(value, bounds, message)
                  for key, (value, bounds, message) in checks.items() if value not in (None, "")}
        if not values:
            raise ValueError("Indica o que guardar: o tempo máximo de resposta, a distância ou o consumo.")
        with locked(self.folder):
            if property_ref not in load_profiles(self.folder, self.config()["account"]):
                raise ValueError("Imóvel desconhecido.")
            panel = load_panel(self.folder, property_ref)
            panel.update(values)
            save_panel(self.folder, property_ref, panel)
            self.log("panel_saved", reference=property_ref, **values)
            return self.panel(property_ref)

    @staticmethod
    def visit_petrol(panel, slots):
        """The petrol a property's visits took: each day with a visit already begun is one round trip to it.
        Days still ahead are counted apart ("planned"), and join the total only once they come."""
        moment = datetime.now().strftime("%Y-%m-%d %H:%M")  # the same local "YYYY-MM-DD HH:MM" as slot["at"]
        done = {slot["at"][:10] for slot in slots if slot["at"] <= moment}
        planned = {slot["at"][:10] for slot in slots if slot["at"] > moment} - done
        distance, consumption = panel["distance_km"], panel["l_per_100km"]
        litres = lambda days: None if distance is None else round(len(days) * 2 * distance * consumption / 100, 1)
        return {"distance_km": distance, "l_per_100km": consumption, "trips": len(done), "planned_trips": len(planned),
                "km": None if distance is None else len(done) * 2 * distance,
                "litres": litres(done), "planned_litres": litres(planned)}

    def require_fuel(self, ref=None):
        """Refuses an API call once that property's tank is empty — here, not only in the page's buttons."""
        if self.api_fuel(ref)["empty"]:
            raise ValueError(f"O depósito da API{' de ' + ref if ref else ''} está vazio: enche-o no painel do imóvel "
                             "(Imóveis) para voltar a usar a API. O copiar/colar com o ChatGPT continua a funcionar.")

    def analyze_visits(self, property_ref=None):
        """Same prompt as visit_analysis_prompt, answered by the OpenAI API instead of pasted by hand."""
        with locked(self.folder):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            if not ref:
                raise ValueError("A análise só existe com imóveis.")
            self.require_fuel(ref)
            data = self.load(ref)
            prompt_text = visit_analysis_prompt(profiles[ref], self.candidates(ref, data), data.get("conversations", {}))
            cfg = self.config()
            key = openai_api_key(self.folder, cfg["account"])
            model = str(cfg.get("openai_model") or MODEL_DEFAULT)
            summary, usage = complete(key, model, prompt_text, json_mode=False)
            self.log("openai_usage", model=model, **usage, reference=ref, cost_usd=round(estimate_cost_usd(model, **{
                k: usage[k] for k in ("prompt_tokens", "completion_tokens")}), 6))
            return {"property_ref": ref, "summary": summary, "tokens": usage, "fuel": self.api_fuel(ref)}

    def agenda_slots(self, ref, today, back_days=14):
        """The booked visits for the agenda: the coming ones and those of the last back_days, so a visit can be
        checked after it happened; each with its check (who came, the notes) and the survey answered."""
        since = (date.fromisoformat(today) - timedelta(days=back_days)).isoformat()
        conversations = self.load(ref).get("conversations", {})
        # Every booking shows whether the customer's file is complete (live: it fills as their answers arrive).
        return sorted(({**slot, "survey": (conversations.get(slot["customer"]) or {}).get("visit_survey"),
                        "ficha": ficha_summary((conversations.get(slot["customer"]) or {}).get("ficha")),
                        "thanks_sent_at": ((conversations.get(slot["customer"]) or {}).get("visit_check") or {}).get("thanks_sent_at")}
                       for slot in load_visits(self.folder, ref)["slots"] if slot["at"][:10] >= since),
                      key=lambda slot: slot["at"])

    def check_visit(self, property_ref, email, attended, private_note="", public_note="", at=None):
        """After the visit, in the agenda: did the customer come, a private note (only for the owner — never in
        an email nor sent to the AI) and a public one (it goes into the thanks)."""
        email = str(email or "").strip().casefold()
        if attended not in (True, False, None):
            raise ValueError("Indica se o cliente apareceu.")
        notes = {key: str(value or "").strip() for key, value in (("private", private_note), ("public", public_note))}
        if any(len(value) > 2000 for value in notes.values()):
            raise ValueError("Nota demasiado longa (até 2000 caracteres).")
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            agenda = load_visits(self.folder, ref)
            slots = sorted((slot for slot in agenda["slots"] if slot.get("customer") == email), key=lambda slot: slot["at"])
            data = self.load(ref)
            conversation = data.get("conversations", {}).get(email)
            if not slots and at and conversation is not None:
                # A time still offered or accepted (blue, orange) the customer did come to: it was the visit.
                try:
                    at = datetime.strptime(str(at).strip(), "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    raise ValueError("Hora de visita inválida.") from None
                agenda["slots"].append({"at": at, "customer": email, "name": conversation.get("name") or "",
                                        "source": "check", "booked_at": now()})
                conversation.pop("visit_offered", None)
                conversation.pop("visit_accepted", None)
                slots = [agenda["slots"][-1]]
            if not slots:
                raise ValueError("Este cliente não tem visita marcada neste imóvel.")
            today = date.today().isoformat()
            slot = next((slot for slot in reversed(slots) if slot["at"][:10] <= today), slots[0])
            slot["check"] = {"attended": attended, **notes, "checked_at": now()}
            save_visits(self.folder, ref, agenda)
            if conversation is not None:
                conversation["visit_check"] = {**(conversation.get("visit_check") or {}), "at": slot["at"],
                                               "attended": attended, **notes}
                self.save(data, ref)
            self.log("visit_checked", reference=ref, attended=attended)
            return {"property_ref": ref, "at": slot["at"], "check": slot["check"]}

    def visit_thanks(self, property_ref, email):
        """«Criar agradecimento»: the after-visit email for a customer who came, a draft in their conversation.
        The assistant writes it with the after-visit prompt (Voz e estilo): thanks, the public note, the
        survey and the visit sheet, in the customer's language. Reviewed and sent like any other draft."""
        email = str(email or "").strip().casefold()
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            conversation = data.get("conversations", {}).get(email)
            check = (conversation or {}).get("visit_check") or {}
            if not conversation or check.get("attended") is not True:
                raise ValueError("Marca primeiro na Agenda que o cliente apareceu na visita.")
            if any(recipient_email(item) == email and item.get("kind") == "visit_thanks" for item in data["emails"]):
                raise ValueError("O agradecimento a este cliente já está na fila.")
            key = f"pos-visita-{hashlib.sha256((email + check.get('at', '')).encode()).hexdigest()[:12]}"
            data["emails"].append(self.aux_item(key, "visit_thanks", email, conversation, "", reply_status="pending",
                                                history=list(conversation.get("history") or []),
                                                visit_done={"at": check.get("at"), "name": conversation.get("name") or "",
                                                            "public": check.get("public") or ""}))
            self.save(data, ref)
            self.log("visit_thanks_created", reference=ref)
            return {"id": key, "property_ref": ref}

    def pending_visits(self, ref, today, field):
        """Times still to be agreed, found in the emails by «Atualizar agenda»: visit_accepted (the customer's,
        orange) or visit_offered (ours, blue). Never for someone booked or ignored."""
        booked = {slot["customer"] for slot in load_visits(self.folder, ref)["slots"] if slot["at"][:10] >= today}
        return sorted(({"at": conversation[field]["at"], "customer": email, "name": conversation.get("name") or "",
                        "evidence": conversation[field].get("evidence") or "", "replaces": conversation[field].get("replaces")}
                       for email, conversation in self.load(ref).get("conversations", {}).items()
                       if (conversation.get(field) or {}).get("at", "")[:10] >= today
                       and email not in booked and not conversation.get("ignored")), key=lambda visit: visit["at"])

    def write_more(self, property_ref, email):
        """«Escrever mais»: one more email to an active customer, a draft in their own conversation (Re: our
        last email). It goes through the queue like any other — prompt or by hand, preview, send — and, being
        an addition, spends no step of the conversation."""
        email = str(email or "").strip().casefold()
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            conversation = data.get("conversations", {}).get(email)
            if not conversation or not conversation.get("sent_message_ids"):
                raise ValueError("Ainda não escreveste a este cliente neste imóvel.")
            if conversation.get("ignored"):
                raise ValueError("Este cliente está na lista a ignorar.")
            if any(recipient_email(item) == email for item in data["emails"]):
                raise ValueError("Este cliente já tem um email na fila: escreve nesse.")
            key = f"acrescento-{hashlib.sha256((email + now()).encode()).hexdigest()[:12]}"
            data["emails"].append(self.aux_item(key, "addition", email, conversation, "", reply_status="pending",
                                                history=list(conversation.get("history") or [])))
            self.save(data, ref)
            self.log("addition_created", reference=ref)
            return {"id": key, "property_ref": ref}

    def remove_active(self, property_ref, email):
        """Takes a sent card out of the queue; it comes back only when that conversation moves again."""
        email = str(email or "").strip().casefold()
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            conversation = data.get("conversations", {}).get(email)
            if not conversation:
                raise ValueError("Cliente desconhecido neste imóvel.")
            conversation["queue_removed_at"] = conversation.get("last_sent_at") or now()
            self.save(data, ref)
            self.log("active_removed", reference=ref)
            return {"removed": 1, "property_ref": ref}

    def sync_agenda(self, property_ref=None):
        """«Atualizar agenda»: the API reads each active customer's conversation — their emails and ours, those
        written straight in Gmail too — and, as the owner chose (25/09), updates the agenda by itself: a day and
        time we confirmed becomes a booked visit (green); one the customer proposed or accepted, still
        unconfirmed, shows orange until then. Customers already booked, who declined or are ignored are not
        asked about, and nothing is ever booked in the past. Every property, or one; a property whose tank is
        empty or whose visits are closed is skipped and says why."""
        with locked(self.folder):
            profiles = self.profiles()
            if not profiles:
                raise ValueError("A agenda só existe com imóveis.")
            cfg = self.config()
            if not has_openai_api_key(self.folder, cfg["account"]):
                raise ValueError("Sem chave da OpenAI: guarda-a com mac/openai_key.command para usar a API.")
            key = openai_api_key(self.folder, cfg["account"])
            model = str(cfg.get("openai_model") or MODEL_DEFAULT)
            today = date.today().isoformat()
            results = []
            for ref in [self.pick(profiles, property_ref)] if property_ref else list(profiles):
                agenda = load_visits(self.folder, ref)
                result = {"property_ref": ref, "confirmed": 0, "moved": 0, "accepted": 0, "offered": 0, "unbooked": 0,
                          "cleared": 0, "asked": 0}
                if agenda.get("closed_at"):
                    results.append({**result, "skipped": "as visitas deste imóvel estão fechadas"})
                    continue
                if self.api_fuel(ref)["empty"]:
                    results.append({**result, "skipped": "o depósito da API está vazio"})
                    continue
                data = self.load(ref)
                conversations = data.get("conversations", {})
                # Everyone active, the booked too: a time changed later in the emails must reach the agenda.
                people = [customer for customer in self.candidates(ref, data) if customer["state"] != "nao_quer"]
                ids = {f"c{number}": customer["email"] for number, customer in enumerate(people, 1)}
                booked = {slot["customer"]: slot for slot in agenda["slots"] if slot["at"][:10] >= today}
                result["asked"] = len(ids)
                if ids:
                    prompt_text = agenda_prompt(profiles[ref], [
                        (key_id, (conversations.get(email) or {}).get("name"), (conversations.get(email) or {}).get("history") or [],
                         (booked.get(email) or {}).get("at")) for key_id, email in ids.items()], today)
                    answer, usage = complete(key, model, prompt_text)
                    self.log("openai_usage", model=model, **usage, reference=ref, cost_usd=round(estimate_cost_usd(
                        model, **{k: usage[k] for k in ("prompt_tokens", "completion_tokens")}), 6))
                    for key_id, found in parse_agenda(answer, set(ids)).items():
                        email = ids[key_id]
                        conversation = conversations[email]
                        slot = booked.get(email)
                        state, at = found["state"], found["at"]
                        if state == "nenhuma" or at[:10] < today:
                            # Never unbooks on a vague answer: only what was pending (orange, blue) is cleared.
                            result["cleared"] += bool(conversation.pop("visit_accepted", None))
                            result["cleared"] += bool(conversation.pop("visit_offered", None))
                            continue
                        conversation.pop("visit_accepted", None)
                        conversation.pop("visit_offered", None)
                        if slot and slot["at"] == at:
                            continue  # the booked time still holds
                        if state == "confirmada":
                            if slot:
                                slot.update(previous=slot["at"], at=at, source="api", evidence=found["evidence"], booked_at=now())
                                result["moved"] += 1
                            else:
                                agenda["slots"].append({"at": at, "customer": email, "name": conversation.get("name") or "",
                                                        "source": "api", "evidence": found["evidence"], "booked_at": now()})
                                result["confirmed"] += 1
                            continue
                        # The latest word is a new time not yet agreed: the old booking no longer holds.
                        pending = {"at": at, "evidence": found["evidence"], "found_at": now()}
                        if slot:
                            agenda["slots"].remove(slot)
                            pending["replaces"] = slot["at"]
                            result["unbooked"] += 1
                        conversation["visit_accepted" if state == "aceite" else "visit_offered"] = pending
                        result["accepted" if state == "aceite" else "offered"] += 1
                    save_visits(self.folder, ref, agenda)
                    self.save(data, ref)
                self.log("agenda_synced", reference=ref, **{k: v for k, v in result.items() if k != "property_ref"})
                results.append({**result, "fuel": self.api_fuel(ref)})
            return {"properties": results}

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
            if load_visits(self.folder, ref).get("closed_at"):
                raise ValueError("Este imóvel já tem as visitas fechadas.")
            data = self.load(ref)
            customers = {customer["email"]: customer for customer in self.candidates(ref, data)}
            for email in chosen:
                if email not in customers:
                    raise ValueError(f"{email} não é cliente deste imóvel.")
                if customers[email]["state"] in ("pending", "booked"):
                    raise ValueError(f"{email}: {customers[email]['reason']}.")
            window["id"] = f"{window['day']}_{window['start']}_{window['end']}".replace(":", "")
            agenda = load_visits(self.folder, ref)
            existing_window = next((w for w in agenda["windows"] if w["id"] == window["id"]), None)
            if existing_window is None:
                existing_window = {**window, "created_at": now(), "recipients": []}
                agenda["windows"].append(existing_window)
            existing_window.setdefault("recipients", [])
            style = load_voice(self.folder).get("style", {})
            first_subject = subject_of("lead", (style.get("reply_subject") or {}).get("text") or None, profiles[ref])
            created = 0
            for email in chosen:
                conversation = data["conversations"][email]
                sent = conversation.get("sent_message_ids") or []
                name = conversation.get("name") or ""
                # Tracked here (not just as a per-email draft) so the owner can look back later at exactly
                # who a given round went to, even after every draft has been sent and left the queue.
                if not any(person["email"] == email for person in existing_window["recipients"]):
                    existing_window["recipients"].append({"email": email, "name": name})
                key = f"visita-{window['id']}-{hashlib.sha256(email.encode()).hexdigest()[:8]}"
                if any(item["id"] == key for item in data["emails"]):
                    continue
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
                    # A snapshot of the conversation so far: the assistant proposes the visit with the
                    # same context it would have for any other reply, not as a message out of nowhere.
                    "history": list(conversation.get("history") or []),
                    "reply_text": "", "send_reply": False, "reply_status": "pending"})
                created += 1
            save_visits(self.folder, ref, agenda)
            self.save(data, ref)
            self.log("visits_proposed", reference=ref, created=created)
            return {"property_ref": ref, "created": created, "window": window}

    def close_visits(self, property_ref=None):
        """One closing draft per customer of this property (pending and already answered), then closes it.

        Closing happens now, at the click, not only once every draft is actually sent: it also switches
        on the auto-reply that the next READ gives to any new lead for this property.
        """
        with locked(self.folder):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            if not ref:
                raise ValueError("As visitas fechadas só existem com imóveis.")
            agenda = load_visits(self.folder, ref)
            if agenda.get("closed_at"):
                raise ValueError("Este imóvel já tem as visitas fechadas.")
            text = (load_voice(self.folder).get("style", {}).get("visits_closed") or {}).get("text") or ""
            if not text:
                raise ValueError("Escreve o texto de «Visitas fechadas» em Voz e estilo antes de usar este botão.")
            data = self.load(ref)
            drafted, handled = 0, set()
            for item in data["emails"]:
                email = ((item.get("recipient") or {}).get("email") or "").casefold()
                if not email:
                    continue
                if item.get("reply_status") in ("sending", "uncertain"):
                    # Leave it: resolve the uncertain send first, and never draft a second email on top of it.
                    handled.add(email)
                    continue
                if item.get("blocked"):
                    continue
                item.update(reply_text=text, reply_status="draft", closing=True)
                handled.add(email)
                drafted += 1
            for email, conversation in data.get("conversations", {}).items():
                if email in handled or conversation.get("ignored") or not (conversation.get("sent_message_ids") or []):
                    continue
                key = f"fecho-{hashlib.sha256(email.encode()).hexdigest()[:8]}"
                if any(item["id"] == key for item in data["emails"]):
                    continue
                data["emails"].append(self.aux_item(key, "visits_closed", email, conversation, text, closing=True))
                drafted += 1
            agenda["closed_at"] = now()
            save_visits(self.folder, ref, agenda)
            self.save(data, ref)
            self.log("visits_closed", reference=ref, drafted=drafted)
            return {"property_ref": ref, "drafted": drafted}

    def request_consent(self, property_ref=None):
        """One consent-request draft per customer who already has a conversation and hasn't been asked."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            if not ref:
                raise ValueError("O pedido de consentimento só existe com imóveis.")
            text = (load_voice(self.folder).get("style", {}).get("consent_request") or {}).get("text") or ""
            if not text:
                raise ValueError("Escreve o texto do pedido de consentimento em Voz e estilo antes de usar este botão.")
            data = self.load(ref)
            waiting = {((item.get("recipient") or {}).get("email") or "").casefold() for item in data["emails"]}
            drafted = 0
            for email, conversation in data.get("conversations", {}).items():
                if (email in waiting or conversation.get("consent_asked") or conversation.get("ignored")
                        or not (conversation.get("sent_message_ids") or [])):
                    continue
                key = f"consentimento-{hashlib.sha256(email.encode()).hexdigest()[:8]}"
                if any(item["id"] == key for item in data["emails"]):
                    continue
                data["emails"].append(self.aux_item(key, "consent_request", email, conversation, text))
                conversation["consent_asked"] = True
                drafted += 1
            self.save(data, ref)
            self.log("consent_requested", reference=ref, drafted=drafted)
            return {"property_ref": ref, "drafted": drafted}

    def confirm_consent(self, message_id, property_ref=None):
        """One click on a suggested "sim/yes/oui" reply: marks the contact's RGPD row and the conversation."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            item = next((e for e in data["emails"] if e["id"] == message_id), None)
            if not item or not item.get("consent_suggested"):
                raise ValueError("Este email não tem um consentimento por confirmar.")
            email = ((item.get("recipient") or {}).get("email") or "").casefold()
            contacts = load_contacts(self.folder)
            row = contacts.get((email, ref))
            if not row:
                raise ValueError("Contacto não encontrado no registo (data/contactos.csv).")
            row.update(rgpd="sim", rgpd_data=date.today().isoformat(), rgpd_prova=str(item.get("message_id") or message_id))
            save_contacts(self.folder, contacts)
            conversation = data.get("conversations", {}).get(email)
            if conversation is not None:
                conversation["consent"] = "sim"
            item.update(consent_suggested=False, consent_confirmed=True)
            self.save(data, ref)
            self.log("consent_confirmed", reference=ref)
            return {"property_ref": ref}

    def sync_contacts(self, profiles):
        """Customers answered before contactos.csv existed get their row too: name and property, and the phone
        when an email of theirs is still in the queue. Their first-contact day is unknown, so it stays blank."""
        entries = []
        for ref in profiles:
            data = self.load(ref)
            phones = {((item.get("recipient") or {}).get("email") or "").casefold(): (item.get("customer") or {}).get("phone")
                      for item in data["emails"]}
            entries += [{"email": email, "nome": conversation.get("name") or "", "telefone": phones.get(email) or "",
                         "primeiro_contacto": "", "imovel": ref, "fonte": CONTACT_SOURCE}
                        for email, conversation in data.get("conversations", {}).items()]
        add_contacts(self.folder, entries)

    def contacts(self):
        """Every contact of contactos.csv, for the Contactos tab, with how many replies each one has had."""
        with locked(self.folder):
            profiles = self.profiles()
            self.sync_contacts(profiles)
            stages = {(email, ref): conversation.get("stage", 0)
                      for ref in profiles for email, conversation in self.load(ref).get("conversations", {}).items()}
            rows = sorted(({**row, "interactions": stages.get((row["email"], row["imovel"]), 0)}
                           for row in load_contacts(self.folder).values()),
                          key=lambda row: (row["imovel"], (row["nome"] or row["email"]).casefold()))
            return {"contacts": rows, "properties": list(profiles), "rgpd_states": RGPD_STATES,
                    "inactive": [ref for ref, profile in profiles.items() if not property_active(profile)],
                    "fichas": [ficha for ref in profiles for ficha in self.fichas(ref, self.load(ref))],
                    "ficha_fields": FICHA_FIELDS}

    def fichas(self, ref, data):
        """Each active customer's file (the ignored ones are left out), the most recent conversation first."""
        agenda = load_visits(self.folder, ref)
        proposed = self.proposed_to(agenda)
        phases = {"booked": "visita marcada", "nao_quer": "não quer visitar", "outra_data": "pediu outra data"}
        found = []
        for customer in self.candidates(ref, data):
            conversation = data["conversations"][customer["email"]]
            came = (conversation.get("visit_check") or {}).get("attended")
            phase = ("visitou" if came is True else "faltou à visita" if came is False else phases.get(customer["state"])
                     or ("proposta de visita" if was_proposed(conversation, customer["email"], proposed) else "qualificação"))
            history = conversation.get("history") or []
            last = max([conversation.get("last_sent_at") or ""] + [turn.get("ts") or turn.get("at") or "" for turn in history])
            ficha = conversation.get("ficha") or {}
            found.append({"property_ref": ref, "email": customer["email"], "name": customer["name"], "phase": phase,
                          "pending": customer["state"] == "pending", "stage": customer["stage"], "last": last,
                          "ficha": {key: ficha.get(key) for key in FICHA_FIELDS}, "updated": ficha.get("at"),
                          **ficha_summary(ficha)})
        return sorted(found, key=lambda item: item["last"], reverse=True)

    def save_contact(self, fields):
        """Adds a contact by hand (a phone call, someone at the door) or edits one; the key is email + property.

        A change of the RGPD state made here is dated, with "alterado à mão" as its proof; the proof of a
        «sim» confirmed from an email (its Message-ID) is kept for as long as the state stays the same.
        """
        email = str(fields.get("email") or "").strip().casefold()
        ref = str(fields.get("imovel") or "").strip()
        if not EMAIL.fullmatch(email):
            raise ValueError("Indica um email válido.")
        clean = {}
        for key, limit in (("nome", 120), ("telefone", 40), ("fonte", 40)):
            clean[key] = " ".join(str(fields.get(key) or "").split())
            if len(clean[key]) > limit:
                raise ValueError(f"Campo demasiado longo: {key}.")
        rgpd = str(fields.get("rgpd") or "por_pedir")
        if rgpd not in RGPD_STATES:
            raise ValueError("Estado RGPD inválido.")
        first = str(fields.get("primeiro_contacto") or "").strip()
        if first and not DAY.fullmatch(first):
            raise ValueError("A data do primeiro contacto tem de ser AAAA-MM-DD.")
        with locked(self.folder):
            if ref not in self.profiles():
                raise ValueError("Escolhe o imóvel do contacto.")
            contacts = load_contacts(self.folder)
            row = contacts.get((email, ref))
            created = row is None
            if created:
                row = contacts[(email, ref)] = {"email": email, "imovel": ref, "rgpd": "por_pedir", "rgpd_data": "",
                                                "rgpd_prova": "", "primeiro_contacto": date.today().isoformat()}
            if first:
                row["primeiro_contacto"] = first
            row.update(nome=clean["nome"], telefone=clean["telefone"], fonte=clean["fonte"] or row.get("fonte") or "Manual")
            if rgpd != row["rgpd"]:
                row.update(rgpd=rgpd, rgpd_data=date.today().isoformat(), rgpd_prova="alterado à mão na página")
            save_contacts(self.folder, contacts)
            self.log("contact_saved", reference=ref, created=created)
            return {"created": created}

    def delete_contact(self, email, property_ref):
        """The right to erasure: the contact's row, conversation, emails in the queue and booked visits all go.

        The Gmail IDs already seen stay (they identify no one), so the same emails are never imported again;
        a new request from the same person starts a new contact, as it should.
        """
        email = str(email or "").strip().casefold()
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            contacts = load_contacts(self.folder)
            row = contacts.pop((email, ref), None)
            data = self.load(ref)
            conversation = data.get("conversations", {}).pop(email, None)
            pending = [item for item in data["emails"]
                       if ((item.get("recipient") or {}).get("email") or (item.get("customer") or {}).get("email")
                           or "").casefold() == email]
            if row is None and conversation is None and not pending:
                raise ValueError("Contacto não encontrado.")
            for item in pending:
                data["emails"].remove(item)
                data["dismissed_message_ids"].extend([item["id"], *item.get("merged_ids", [])])
            agenda = load_visits(self.folder, ref)
            slots = [slot for slot in agenda["slots"] if slot.get("customer") != email]
            if len(slots) != len(agenda["slots"]):
                agenda["slots"] = slots
                save_visits(self.folder, ref, agenda)
            data.pop("send_preview", None)
            save_contacts(self.folder, contacts)
            self.save(data, ref)
            self.log("contact_deleted", reference=ref, pending=len(pending))
            return {"pending_removed": len(pending), "conversation_removed": conversation is not None}

    def set_ignored(self, property_ref, email, ignored=True, reason="", kind=None):
        """Ignore list, per property: unlike "Retirar da fila" (one email, once), this covers every future
        message from them too — they stop being a visit candidate and stop getting reminders, consent
        requests or the closing email. Nothing is deleted (unlike the RGPD erasure): the conversation and
        its history stay, only muted. reason is free text (e.g. "cliente disse que não tem interesse"),
        kept only to explain later why someone is on the list — it changes nothing about the effect.
        kind: "black" (the owner decided): nothing of theirs comes in again. "grey" (the customer opted out):
        we never write first again, but what they write still comes in (see shut_out)."""
        email = str(email or "").strip().casefold()
        if not email:
            raise ValueError("Falta o email do contacto.")
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            if not ref:
                raise ValueError("A lista a ignorar só existe com imóveis.")
            data = self.load(ref)
            conversation = data["conversations"].setdefault(email, {})
            conversation["ignored"] = bool(ignored)
            conversation["ignored_reason"] = " ".join(str(reason or "").split())[:300] if ignored else ""
            conversation["ignored_kind"] = ((kind if kind in IGNORE_KINDS else "grey" if reason else "black")
                                            if ignored else "")
            removed = 0
            if ignored:
                pending = [item for item in data["emails"]
                          if ((item.get("recipient") or {}).get("email") or "").casefold() == email]
                for item in pending:
                    data["emails"].remove(item)
                    data["dismissed_message_ids"].extend([item["id"], *item.get("merged_ids", [])])
                removed = len(pending)
            self.save(data, ref)
            self.log("contact_ignored" if ignored else "contact_unignored", reference=ref)
            return {"property_ref": ref, "email": email, "ignored": bool(ignored), "removed": removed}

    def ignored_contacts(self, property_ref=None):
        """Who is on the ignore list for a property, and why (when known), to review or undo."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            if not ref:
                raise ValueError("A lista a ignorar só existe com imóveis.")
            data = self.load(ref)
            customers = [{"email": email, "name": conversation.get("name") or "",
                         "reason": conversation.get("ignored_reason") or "", "kind": ignore_kind(conversation)}
                        for email, conversation in data.get("conversations", {}).items() if conversation.get("ignored")]
            return {"property_ref": ref, "customers": sorted(customers, key=lambda c: c["email"])}

    def contacts_csv(self):
        """contactos.csv as it is on disk, for the page's download button (after bringing in older customers)."""
        with locked(self.folder):
            self.sync_contacts(self.profiles())
            path = self.folder / "contactos.csv"
            text = path.read_bytes() if path.exists() else (",".join(CONTACT_FIELDS) + "\r\n").encode()
            return b"\xef\xbb\xbf" + text  # the UTF-8 mark, so Excel shows accents (ç, ã) right

    def voice_ready(self):
        try:
            load_voice(self.folder)
            return True
        except ValueError:
            return False

    def openai_ready(self):
        """Whether «Gerar respostas via API» has a key to use; optional, Copiar/colar works without it."""
        try:
            return has_openai_api_key(self.folder, self.config()["account"])
        except ValueError:
            return False

    def metrics(self, days=14):
        """Numbers for the dashboard. Of the customers, only first names leave this call: no address or phone.

        days: the chart's period, one of CHART_PERIODS; 3 months are drawn one bar per week, not per day.
        """
        if days not in CHART_PERIODS:
            raise ValueError("Período inválido: escolhe 3, 7, 14, 30 ou 90 dias.")
        step = CHART_PERIODS[days]
        today = datetime.now(timezone.utc).date()
        first = today - timedelta(days=days - 1)

        def bucket(value):
            try:
                day = date.fromisoformat(str(value or "")[:10])
            except ValueError:
                return None
            if not first <= day <= today:
                return None
            return (first + timedelta(days=(day - first).days // step * step)).isoformat()

        with locked(self.folder):
            account = self.config()["account"]
            profiles = load_profiles(self.folder, account)
            refs = list(profiles) or [None]
            contacts = load_contacts(self.folder)
            events = load_events(self.folder, limit=100000)  # read once: the chart, the costs and every tank
            # A customer email, by message ID → the day it arrived. Three sources, most exact first:
            # the day logged at READ; the email still in the queue; a sent reply's time minus the hours the
            # customer waited (older emails that left the queue before READ logged the day).
            arrived, derived, totals, properties, last_read = {}, {}, Counter(), [], None
            # Which property each message ID belongs to: the queue, and the replied and dismissed IDs every
            # queue keeps for good. Old log events carry no property; this is how they are attributed.
            owner = {}
            today_iso = today.isoformat()
            for ref in refs:
                data = self.load(ref)
                emails = data["emails"]
                status = Counter(item.get("reply_status") or "pending" for item in emails)
                blocked = sum(1 for item in emails if item.get("blocked"))
                conversations = data.get("conversations", {})
                answered = sum(conversation.get("stage", 0) for conversation in conversations.values())
                for message_id in ({item["id"] for item in emails} | set(data.get("replied_message_ids") or [])
                                   | set(data.get("dismissed_message_ids") or [])):
                    owner.setdefault(str(message_id), ref)
                slots = load_visits(self.folder, ref)["slots"] if ref else []
                clients = Counter(customer["state"] for customer in self.candidates(ref, data)) if ref else Counter()
                ignored = Counter(ignore_kind(c) for c in conversations.values() if c.get("ignored"))
                for item in emails:
                    if item.get("kind") not in PROGRAM_KINDS:
                        derived.setdefault(item["id"], str(item.get("date") or "")[:10])
                # The one exception to "no customer data" on the dashboard (22/09): first name, dates and
                # how many replies, for the hover of «Respostas enviadas». Never an address or a phone.
                customers = sorted(({"name": ((conversation.get("name") or "").split() or ["(sem nome)"])[0],
                                     "first_contact": (contacts.get((email, ref)) or {}).get("primeiro_contacto") or None,
                                     "last_reply": str(conversation.get("last_sent_at") or "")[:10] or None,
                                     "interactions": conversation.get("stage", 0)}
                                    for email, conversation in conversations.items() if conversation.get("stage")),
                                   key=lambda customer: customer["last_reply"] or "", reverse=True)
                totals.update(pending=len(emails), drafts=status["draft"], blocked=blocked, answered=answered,
                              customers=len(conversations),
                              attention=status["uncertain"] + status["error"] + status["sending"])
                last_read = max([stamp for stamp in (last_read, data.get("last_read_at")) if stamp], default=None)
                listing = profiles[ref]["property"] if ref else {}
                properties.append({"property_ref": ref, "pending": len(emails), "drafts": status["draft"],
                                   "blocked": blocked, "answered": answered, "customers": len(conversations),
                                   "attention": status["uncertain"] + status["error"] + status["sending"],
                                   "visits_booked": sum(1 for slot in slots if slot["at"][:10] >= today_iso),
                                   "reply_hours_max": self.panel(ref)["reply_hours_max"],
                                   "api_fuel": self.api_fuel(ref, events),
                                   "petrol": self.visit_petrol(self.panel(ref), slots),
                                   "clients": {state: clients[state] for state in
                                               ("ok", "pending", "booked", "outra_data", "nao_quer")},
                                   "ignored": {kind: ignored[kind] for kind in IGNORE_KINDS},
                                   "answered_customers": customers,
                                   "last_read_at": data.get("last_read_at"), "description": listing.get("description"),
                                   "listing_url": listing.get("listing_url"),
                                   "advertised_rent_eur": listing.get("advertised_rent_eur"),
                                   "photo": bool(ref) and find_photo(self.folder, ref) is not None})
            sent, waited = Counter(), []
            openai_period, openai_all_time, unattributed = Counter(), Counter(), Counter()
            per = {ref: {"requests": Counter(), "sent": Counter(), "waited": [], "period": Counter(),
                         "all_time": Counter()} for ref in refs}
            for event in events:
                if event.get("event") == "read" and isinstance(event.get("received"), dict):
                    arrived.update(event["received"])
                elif event.get("event") == "send" and event.get("status") == "sent":
                    sent[bucket(event.get("at"))] += 1
                    ref = event.get("reference") or owner.get(str(event.get("message_id")))
                    if ref in per:
                        per[ref]["sent"][bucket(event.get("at"))] += 1
                    hours = event.get("waited_hours")
                    if isinstance(hours, (int, float)) and event.get("kind") not in PROGRAM_KINDS:
                        waited.append(hours)
                        if ref in per:
                            per[ref]["waited"].append(hours)
                        try:
                            day = (datetime.fromisoformat(event["at"]) - timedelta(hours=hours)).date().isoformat()
                        except (KeyError, TypeError, ValueError):
                            continue
                        derived.setdefault(str(event.get("message_id")), day)
                elif event.get("event") == "openai_usage":
                    # Never the prompt or the answer, only what was logged at the time: tokens and an
                    # estimated cost (see openai_client.PRICE_PER_1K_USD — OpenAI's own rates can move).
                    usage = Counter(calls=1, prompt_tokens=event.get("prompt_tokens", 0),
                                    completion_tokens=event.get("completion_tokens", 0),
                                    cost_usd=event.get("cost_usd", 0))
                    openai_all_time.update(usage)
                    in_period = bucket(event.get("at")) is not None
                    if in_period:
                        openai_period.update(usage)
                    # Logged with its property since 24/09; before that there is no way to tell which one.
                    if "reference" in event and event["reference"] in per:
                        per[event["reference"]]["all_time"].update(usage)
                        if in_period:
                            per[event["reference"]]["period"].update(usage)
                    else:
                        unattributed.update(usage)
            merged = {**derived, **arrived}
            requests = Counter(bucket(day) for day in merged.values())
            for message_id, day in merged.items():
                ref = owner.get(str(message_id))
                if ref in per:
                    per[ref]["requests"][bucket(day)] += 1
            starts = [(first + timedelta(days=n)).isoformat() for n in range(0, days, step)]

            def usage_of(counter):
                return {"calls": counter["calls"], "prompt_tokens": counter["prompt_tokens"],
                        "completion_tokens": counter["completion_tokens"], "cost_usd": round(counter["cost_usd"], 4)}

            for item in properties:
                mine = per[item["property_ref"]]
                item.update(by_day=[{"day": day, "requests": mine["requests"].get(day, 0),
                                     "sent": mine["sent"].get(day, 0)} for day in starts],
                            reply_hours=round(sum(mine["waited"]) / len(mine["waited"]), 1) if mine["waited"] else None,
                            openai_usage={"period": usage_of(mine["period"]), "all_time": usage_of(mine["all_time"])})
            return {"account": account, "last_read_at": last_read, "properties": properties,
                    "totals": {key: totals[key] for key in
                               ("pending", "drafts", "blocked", "attention", "answered", "customers")},
                    "period_days": days, "bucket_days": step,
                    "by_day": [{"day": day, "requests": requests.get(day, 0), "sent": sent.get(day, 0)}
                               for day in starts],
                    "reply_hours": round(sum(waited) / len(waited), 1) if waited else None,
                    "openai_usage": {"period": usage_of(openai_period), "all_time": usage_of(openai_all_time),
                                     "unattributed": usage_of(unattributed)},
                    "api_fuel": self.api_fuel(None, events),
                    "setup": {"account": bool(account), "app_password": has_app_password(self.folder, account),
                              "voice": self.voice_ready(), "properties": len(profiles),
                              "openai_key": has_openai_api_key(self.folder, account)}}

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
            reminders = style.get("reminders") or {}
            voice["reminders"] = {key: (reminders.get(key) or {}).get("text") or "" for key in ("day2", "day4")}
            voice["visits_closed"] = (style.get("visits_closed") or {}).get("text") or ""
            voice["consent_request"] = (style.get("consent_request") or {}).get("text") or ""
            voice["after_visit"] = (style.get("after_visit") or {}).get("text") or AFTER_VISIT_RULE
            voice["after_visit_template"] = (style.get("after_visit_template") or {}).get("text") or AFTER_VISIT_TEMPLATE
            voice["digest_recipient"] = (style.get("digest_recipient") or {}).get("text") or ""
            today = date.today().isoformat()
            properties = []
            events = load_events(self.folder, limit=100000)  # once, for every property's tank
            for ref, profile in load_profiles(self.folder, account).items():
                prompts = profile.get("reply", {}).get("prompts", {})
                properties.append({"sender": profile["match"]["from_address_equals"], "active": property_active(profile),
                                   "prompts": {name: (prompts.get(key) or {}).get(field) or ""
                                               for name, (key, field) in PROMPT_FIELDS.items()},
                                   "knowledge_files": [part["file"] for part in profile["_knowledge"]],
                                   "photo": find_photo(self.folder, ref) is not None,
                                   "api_fuel": self.api_fuel(ref, events),
                                   "visits": {"windows": [window for window in load_visits(self.folder, ref)["windows"]
                                                          if window["day"] >= today],
                                              "slots": self.agenda_slots(ref, today),
                                              "closed_at": load_visits(self.folder, ref)["closed_at"],
                                              # Accepted by the customer, not yet confirmed (found by «Atualizar agenda»).
                                              "accepted": self.pending_visits(ref, today, "visit_accepted"),
                                              "offered": self.pending_visits(ref, today, "visit_offered")},
                                   **{key: profile["property"].get(key) for key in (
                                       "reference", "listing_id", "listing_url", "advertiser", "description",
                                       "advertised_rent_eur")}})
            return {"account": account, "voice": voice, "properties": properties,
                    "lookback_days": int(self.config().get("lookback_days", 7)),
                    "openai_configured": has_openai_api_key(self.folder, account), "api_fuel": self.api_fuel(None, events)}

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
            reminders = choices.get("reminders")
            if reminders is not None:
                if not isinstance(reminders, dict):
                    raise ValueError("Lembretes inválidos.")
                texts = {key: " ".join(str(reminders.get(key) or "").split()) for key in ("day2", "day4")}
                if any(len(value) > 300 for value in texts.values()):
                    raise ValueError("A frase do lembrete é demasiado longa (até 300 caracteres).")
                for key, text in texts.items():
                    style.setdefault("reminders", {}).setdefault(key, {}).update(
                        text=text, status="configured" if text else "not_configured")
            for key, default in (("after_visit", AFTER_VISIT_RULE), ("after_visit_template", AFTER_VISIT_TEMPLATE)):
                if key in choices:
                    text = str(choices.get(key) or "").strip()
                    if len(text) > 5000:
                        raise ValueError("Texto demasiado longo (até 5000 caracteres).")
                    same = " ".join(text.split()) == " ".join(default.split())  # left as it came: keep following the code
                    style.setdefault(key, {}).update(text="" if same else text,
                                                     status="configured" if text and not same else "not_configured")
            for key in ("visits_closed", "consent_request"):
                if key in choices:
                    text = str(choices.get(key) or "").strip()
                    if len(text) > 3000:
                        raise ValueError("Texto demasiado longo (até 3000 caracteres).")
                    style.setdefault(key, {}).update(text=text, status="configured" if text else "not_configured")
            if "digest_recipient" in choices:
                recipient = str(choices.get("digest_recipient") or "").strip()
                if recipient and not EMAIL.fullmatch(recipient):
                    raise ValueError("O destinatário do ponto de situação tem de ser um endereço de email.")
                style.setdefault("digest_recipient", {}).update(
                    text=recipient, status="configured" if recipient else "not_configured")
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

    def set_property_active(self, ref, active):
        """ATIVO / INATIVO (26/09): an inactive property leaves the page's property menus, but still shows in
        Imóveis and keeps everything it has; nothing else changes (emails are still read and answered)."""
        if not isinstance(active, bool):
            raise ValueError("Indica se o imóvel fica ativo ou inativo.")
        with locked(self.folder):
            profiles = load_profiles(self.folder, self.config()["account"])
            if ref not in profiles:
                raise ValueError("Imóvel desconhecido.")
            profile = profiles[ref]
            profile.pop("_knowledge", None)  # runtime only, never written to profile.json
            if active:
                profile.pop("active", None)  # active is the default: nothing to store
            else:
                profile["active"] = False
            save_json(self.folder / "properties" / ref / "profile.json", profile)
            self.log("property_active" if active else "property_inactive", reference=ref)
            return {"reference": ref, "active": active}

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
