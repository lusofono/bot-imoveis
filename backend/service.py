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
import subprocess
import sys
import time
import os
from . import APP_NAME
from .ai import (AFTER_VISIT_RULE, AFTER_VISIT_TEMPLATE, BOOKED_REPLY_RULE, DOCS_REQUEST_RULE, KNOWLEDGE_RULE, VISIT_REMINDER_RULE, VISITED_REPLY_RULE, extract_json, ficha_profile_prompt,
                 REMINDER_RULE, SURVEY_REPLY_RULE, VISIT_MISSED_RULE, CLOSING_FROM, CLOSING_REPLY_RULE, LATER_REPLY_RULE,
                 CONCLUSIVE_AT, CONCLUSIVE_REPLY_RULE, ALERT_KINDS, OWNER_REPLY_RULE, owner_prompt,
                 SHORTLIST_REQUEST_RULE, SHORTLIST_DOCS_RULE,
                 fichas_prompt, parse_fichas_batch,
                 listing_text_prompt, parse_listing, agenda_prompt, describe, instructions,
                 parse_agenda, parse_survey, visit_analysis_prompt, clean_round, round_text)
from .configure import STARTER, example_profile
from .evaluator import evaluation_prompt, parse_evaluations, text_hash
from .mail import build_digest, build_reply, read_messages
from .openai_client import (BUILTIN_CONTEXT, BUILTIN_PRICES, CONTEXT_FALLBACK, EFFORTS, MODEL_DEFAULT, PRICE_PER_1K_USD,
                            REASONING, apply_context, apply_effort, apply_hidden, apply_prices, complete, context_of,
                            estimate_cost_usd, models, HIDDEN)
from .rules import (after_workdays, DAY, DEALS, EMAIL, KNOWLEDGE_FILE, deal_of, RGPD_STATES, SUBJECT_DEFAULT, VISIT_SLOT_DEFAULT, VISIT_STATES,
                    DOCUMENTS, FICHA_FIELDS, SELECTION_STATES, build_profile, check_profile, clean_ficha, documents_summary, draft_checks,
                    ficha_summary, merge_ficha,
                    survey_alerts, survey_report, check_slot, check_window, clean_property, consent_yes, free_times,
                    knowledge, photo_of, prepare, property_active, route, subject_of, QUOTE, addresses, has_token,
                    apply_portal, parse_call, call_notice, phone_key)
from . import portals
from .secrets import app_password, has_app_password, has_openai_api_key, openai_api_key, tag_key
from . import mark
from .store import (CONTACT_FIELDS, add_contacts, add_note, find_photo, knowledge_files, load_contacts, load_digest,
                    load_notices, save_notices, load_calls, save_calls,
                    load_events, load_knowledge, load_panel, load_visits, locked, load_json, load_profiles, load_voice,
                    property_folder, read_photo, save_contacts, save_digest, save_json, save_panel, save_text,
                    save_visits, write_photo)

CONTACT_SOURCE = "Idealista"  # today's only portal; see README for the family of emails it accepts.
# Sent automatically or by a one-click button, in the customer's conversation, but never counted as one
# of the four interactions and never resetting the clock the 2/4-day reminders are measured from.
AI_MODES = ("api", "copy_paste")
AUX_KINDS = {"reminder", "consent_request", "visits_closed", "addition", "visit_thanks", "visit_reminder", "docs_request",
             "visit_missed"}  # "addition": «Escrever mais»; "visit_thanks": after the visit
PROGRAM_KINDS = AUX_KINDS | {"visit_proposal"}  # drafts the program creates; not an email a customer sent
REMINDER_HOURS = {"2d": 48, "4d": 96}
REMINDER_MAX_HOURS = 144  # 6 days of silence: no more reminders (26/09)
FICHAS_BATCH = 10  # customers per call in «Preencher fichas com a IA»
CONTACT_RETENTION_DAYS = 183  # 6 months without consent (decided 21/09); erased on the owner's click
FIRST_READ_DAYS = 45  # 27/09: how far back a property's first read goes, unless chosen when it was created
FIRST_READ_RANGE = (1, 365)
REPLY_TIME_DAYS = 5  # 06/10: the two average reply times count only the last five days (the owner's choice)
NO_REPLY_DAYS = 3  # 27/09: our last email unanswered this long puts the customer in «Sem resposta», at any step
# 27/09: the dots in the customers table, in hours, set in Voz e estilo: orange, a message of theirs waiting for us
# longer than this; blue, their file complete this long and still no visit date from us.
ALERT_HOURS = {"our_turn_hours": 48, "no_visit_hours": 96}
ALERT_HOURS_RANGE = (1, 720)
SURVEY_NOTICE = "Resposta ao inquérito pós-visita registada (vê-a em Visitas e no relatório do imóvel)."
# 06/10: silence in two steps (the owner's rule; until then, inactive after two unanswered, the last four days old):
# «ausente» when the 3rd email of ours in a row is 48 hours without an answer — only marked, still in the rounds and the
# reminders; «inativo» when the 4th is two working days without one — out of them. Their next email brings them back.
ABSENT_AFTER_EMAILS, ABSENT_AFTER_HOURS = 3, 48
INACTIVE_AFTER_EMAILS, INACTIVE_AFTER_WORKDAYS = 4, 2
HISTORY_LIMIT = 20  # turns kept per conversation, oldest dropped first; also what the prompt gets
REPORT_SIGNATURE = f"{APP_NAME} Assistente"  # how the ponto de situação signs (27/09), not the agency's voice
INTERACTION_MARGIN = 0.20  # 27/09: the safety margin on the average cost of an interaction, for quoting a client
# The client price per 100 interactions is quoted in euros, at this rate (tradingeconomics.com, 27/09/2026). The rest of
# the page keeps 1 € = 1 US$ (the owner's choice, 24/09). Update it by hand when the dollar moves a lot.
USD_PER_EUR, USD_PER_EUR_DATE = 1.1382, "2026-09-27"
# Dashboard chart: period in days → days per bar (90 days per day would be 90 unreadable bars).
CHART_PERIODS = {3: 1, 7: 1, 14: 1, 30: 1, 90: 7}
SHORT_WAIT = 10  # 02/10: seconds a short operation (the queue, the drafts) waits its turn instead of failing at once
ADDITION_MIN_TEXT = 20  # 30/09: an «acrescento» with less text than this goes when the customer writes again
REVIEW_MIN_TEXT = 40  # 30/09: a draft shorter than this is not reviewed (a mark on 3 letters means nothing)
CONTEXT_SHARE, BATCH_EMAILS = 50, 5
HIDDEN_DEFAULT_OF = lambda cfg: cfg["hidden_models"] if "hidden_models" in cfg else ("gpt-4o", "gpt-4.1", "gpt-6-astra")  # 29/09: one call's limits by default (Oficina): % of the model's context, emails

VIEW_FIELDS = ("id", "kind", "date", "subject", "customer", "recipient", "blocked", "body_text", "body_truncated",
               "reply_text", "reply_status", "reply_error", "reply_message_id", "visit_window", "visit_slot",
               "visit_status", "reminder", "closing", "consent_suggested", "consent_confirmed", "history", "merged",
               "merged_ids", "visit_done", "visit_reminder", "survey_reply", "docs_request", "visit_missed", "profile_url",
               "round", "review", "attachments", "addition_note", "addition_scope", "reply_note")
# 30/09: the prompts common to every property that the Oficina edits (voice.json), with the code's own text; the
# behaviour («Comportamento geral») lives at the root of voice.json, the others under style.
COMMON_PROMPTS = {"application_instructions": "", "after_visit": AFTER_VISIT_RULE, "after_visit_template": AFTER_VISIT_TEMPLATE,
                  "visit_reminder": VISIT_REMINDER_RULE, "booked_reply": BOOKED_REPLY_RULE, "visited_reply": VISITED_REPLY_RULE,
                  "docs_request": DOCS_REQUEST_RULE, "survey_reply": SURVEY_REPLY_RULE, "reminder_rule": REMINDER_RULE,
                  "visit_missed": VISIT_MISSED_RULE, "later_reply": LATER_REPLY_RULE,
                  "conclusive_reply": CONCLUSIVE_REPLY_RULE, "closing_reply": CLOSING_REPLY_RULE,
                  "owner_reply": OWNER_REPLY_RULE, "shortlist_request": SHORTLIST_REQUEST_RULE, "shortlist_docs": SHORTLIST_DOCS_RULE}
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
# 02/10: the backups — the data folder, zipped once a day (at the first read) into a folder the owner chose; the keys
# never go (data/secrets/, the Keychain), nor the lock and temporary files. Nothing is ever deleted: only added (each is
# under 1 MB). Google Drive for desktop's folder on this Mac is offered (the Gmail App Password gives no Drive access).
BACKUP_PREFIX = "ARIA-copia-"
DRIVE_NAMES = ("My Drive", "O meu disco", "Meu Drive", "A minha unidade")
OWNER_FOLDER = "proprietarios"  # 02/10: the agency's know-how for owners, in data/proprietarios/knowledge/
CAIXA = "_caixa"  # 03/10: the inbox of the owners with no property in the ARIA (data/proprietarios/caixa.json)
def owner_folder(folder, email):
    """02/10: one owner's own knowledge, in data/proprietarios/donos/<their email, as a folder name>/knowledge/."""
    return Path(folder) / OWNER_FOLDER / "donos" / re.sub(r"[^a-z0-9]+", "-", str(email or "").casefold()).strip("-")


NOTICES_KEPT = 300  # 02/10: the notice board keeps the latest ones; the oldest finished ones fall off first
NOTICE_NOTE_CHARS = 25  # 04/10: the owner's own short note on a notice
AUTO_READ_MINUTES = 10  # 06/10: Emails reads by itself when the last read is older than this (Settings changes it)
# 04/10: the owner's own mark on a notice, the post-it's colour: urgent red, not urgent blue, dealt with green
NOTICE_MARKS = ("urgent", "calm", "done")
NOTICE_EVENT_DAYS = 7  # 04/10: a green or grey notice (news, nothing to do) leaves the board after a week
# 04/10: five levels, the colour of the board's pin — ok (green, all well), info (grey), watch (yellow), warn (orange,
# needs you), bad (red, urgent)
NOTICE_LEVELS = ("ok", "info", "watch", "warn", "bad")
WAITING_NOTICE_HOURS = 72  # 02/10: a customer waiting this long for our answer is on the board (once a day)
FUEL_DEFAULT_EUR = 5.0
FUEL_TEST_EUR = 3.0  # 02/10: the test property's tank, unless the owner fills it with another amount
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


def survey_of(conversation):
    """The customer's survey answer as read today: one kept before 26/09 without any mark (written as words, or over
    two lines) is read again, on the spot, from their own reply in the history; nothing is written."""
    survey = (conversation or {}).get("visit_survey")
    if not survey or any(survey.get(part) for part in ("imovel", "consultor", "marcacao")):
        return survey
    for turn in reversed(conversation.get("history") or []):
        again = parse_survey(turn["text"]) if turn.get("who") == "cliente" else None
        if again and any(again.get(part) for part in ("imovel", "consultor", "marcacao")):
            return {**again, "at": survey.get("at")}
    return survey


def ficha_update(old, new):
    """merge_ficha, stamped: "at" is this update; "complete_at", when the file first became complete, kept while it
    stays complete (a file complete before 27/09 counts from its last update)."""
    merged, at = merge_ficha(old, new), now()
    if not ficha_summary(merged)["complete"]:
        return {**merged, "at": at}
    since = ((old or {}).get("complete_at") or (old or {}).get("at")) if ficha_summary(old)["complete"] else None
    return {**merged, "at": at, "complete_at": since or at}


def alert_hours(voice):
    """The hours behind the orange and blue dots, as set in Voz e estilo (ALERT_HOURS by default)."""
    stored = ((voice or {}).get("style") or {}).get("alerts") or {}
    return {key: int(stored.get(key) or default) for key, default in ALERT_HOURS.items()}


def was_proposed(conversation, email, proposed):
    """A visit was already proposed to them: by a round (proposed: everyone ever invited or booked), or as the
    conversation shows (offered, accepted, another date asked, or checked after a visit)."""
    return bool(email in proposed or conversation.get("visit_proposed") or conversation.get("visit_offered")
                or conversation.get("visit_accepted") or conversation.get("visit") == "outra_data"
                or conversation.get("visit_check"))


SHOWN_NAME_CHARS = 22  # 04/10: a customer's name on the page and the board, cut at about this length


def shown_name(name, fallback="sem nome"):
    """04/10: a customer as the owner sees them, everywhere (notices, «A fazer», the Painel, the reports): the first name
    and the last surname — never one name alone when there are more — cut at about SHOWN_NAME_CHARS with «…». Only for
    the owner's eyes: the AI still gets the first name only (ai.first_name)."""
    words = str(name or "").split()
    if not words:
        return fallback
    text = words[0] if len(words) == 1 else f"{words[0]} {words[-1]}"
    return text if len(text) <= SHOWN_NAME_CHARS else text[:SHOWN_NAME_CHARS - 1].rstrip() + "…"


def waited_hours(item):
    """Hours between the customer's email and now, or None when the email had no usable date."""
    try:
        arrived = datetime.fromisoformat(str(item.get("date") or ""))
    except ValueError:
        return None
    if arrived.tzinfo is None:
        arrived = arrived.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - arrived).total_seconds() / 3600, 1)


def client_reply_hours(conversations, since=None):
    """06/10: how long the customers take to answer us, on average: from our email they answered (the last of ours before
    their message) to their message, in hours. Only turns with their exact time (ts), and since: their answers from then
    on; None without any."""
    hours = []
    for conversation in (conversations or {}).values():
        history = conversation.get("history") or []
        for before, turn in zip(history, history[1:]):
            if before.get("who") == "nos" and turn.get("who") == "cliente":
                ours, theirs = aware(before.get("ts") or ""), aware(turn.get("ts") or "")
                if ours and theirs and theirs > ours and (since is None or theirs >= since):
                    hours.append((theirs - ours).total_seconds() / 3600)
    return round(sum(hours) / len(hours), 1) if hours else None


def no_reply_share(conversations):
    """06/10: of the customers we wrote to, how many never answered any email of ours (they never count in the average
    above: it only has answers): {"written", "never"}."""
    written = never = 0
    for conversation in (conversations or {}).values():
        history = conversation.get("history") or []
        first = next((index for index, turn in enumerate(history) if turn.get("who") == "nos"), None)
        if first is None:
            continue
        written += 1
        never += not any(turn.get("who") == "cliente" for turn in history[first + 1:])
    return {"written": written, "never": never}


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


# 04/10, «Escrever a todos»: to every active customer of a property, or only to those who have not answered our last email
WRITE_ALL_AUDIENCES = ("all", "unanswered")


def write_all_targets(data):
    """Who «Escrever a todos» reaches in a property: everyone we have written to (all), and those whose last turn is
    ours (unanswered) — never the blacklist or the greylist, who said they do not want to visit, or a closed contact.
    queued: those left out because an email of theirs is in the queue already (answered there, with step 2's extras)."""
    busy = {recipient_email(item) for item in data.get("emails") or []}
    targets = {"all": [], "unanswered": [], "queued": []}
    for email, conversation in (data.get("conversations") or {}).items():
        if (not conversation.get("sent_message_ids") or conversation.get("ignored") or conversation.get("visit") == "nao_quer"
                or conversation.get("closed_at")):
            continue
        if email in busy:
            targets["queued"].append(email)
            continue
        targets["all"].append(email)
        history = conversation.get("history") or []
        if history and history[-1].get("who") == "nos":
            targets["unanswered"].append(email)
    return targets


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
        self.reading = {}  # 02/10: the read in progress (stage, number of total, sender, subject); empty when none
        self.path = self.folder / "queue.json"

    def config(self):
        """config.json, with a usable account; nothing starts without one."""
        cfg = load_json(self.folder / "config.json", {})
        apply_prices(cfg.get("token_prices"))  # 29/09: the Oficina's token prices, for every estimate from here
        apply_context(cfg.get("model_context"))
        apply_effort(cfg.get("reasoning_effort"))  # 02/10: how much the model reasons (Oficina)
        apply_hidden(cfg.get("hidden_models"))  # 02/10: the models not offered (old and dear, or above 3 €)
        apply_portal(cfg.get("portal"))  # 02/10: the portal's senders and rules (Oficina)
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

    def ai_mode(self):
        """«Modo: só API» (26/09), on unless config.json says "ai_mode": "copy_paste": then the page shows the
        ChatGPT copy/paste again. The MCP (mcp.py) only runs if the Claude Desktop is set to start it."""
        mode = load_json(self.folder / "config.json", {}).get("ai_mode")
        return mode if mode in AI_MODES else "api"

    def model(self, cfg=None):
        """The one model for everything (replies, agenda, analysis, listings); an unknown one reads as the default."""
        cfg = cfg if cfg is not None else load_json(self.folder / "config.json", {})
        apply_prices(cfg.get("token_prices"))
        apply_hidden(cfg.get("hidden_models"))
        model = cfg.get("openai_model")
        return model if model in models() else MODEL_DEFAULT

    def set_model(self, model):
        """The page's model choice, kept in config.json with everything else there untouched."""
        self.model()  # the Oficina's prices, with any model of its own
        if model not in models():
            raise ValueError("Modelo desconhecido: escolhe " + " ou ".join(models()) + ".")
        with locked(self.folder):
            cfg = load_json(self.folder / "config.json", {})
            cfg["openai_model"] = model
            save_json(self.folder / "config.json", cfg)
            self.log("model_set", model=model)
            return self.ai_settings()

    def interaction_cost(self, events=None):
        """27/09: what an interaction costs here, on average, for quoting a client: every token the API used (replies,
        files, agenda, analysis, listings), over the emails this folder sent since the API's first call — not the
        replies the owner wrote in Gmail —, plus INTERACTION_MARGIN. Tokens in and out apart: their prices differ."""
        events = load_events(self.folder, limit=100000) if events is None else events
        calls = [event for event in events if event.get("event") == "openai_usage"]
        first = min((str(event.get("at") or "") for event in calls), default="")
        sent = sum(1 for event in events if first and event.get("event") == "send" and event.get("status") == "sent"
                   and event.get("kind") != "direct" and str(event.get("at") or "") >= first)
        tokens = {key: sum(event.get(key) or 0 for event in calls) for key in ("prompt_tokens", "completion_tokens")}
        per_100 = {}
        if sent:
            average = {key: value / sent * (1 + INTERACTION_MARGIN) for key, value in tokens.items()}
            per_100 = {model: round(100 * (average["prompt_tokens"] * rates[0] + average["completion_tokens"] * rates[1]) / 1000, 4)
                       for model, rates in PRICE_PER_1K_USD.items()}
        return {"interactions": sent, "since": first[:10] or None, **tokens, "margin": INTERACTION_MARGIN, "per_100_usd": per_100,
                "per_100_eur": {model: round(value / USD_PER_EUR, 4) for model, value in per_100.items()},
                "usd_per_eur": USD_PER_EUR, "rate_date": USD_PER_EUR_DATE}

    def ai_settings(self, events=None):
        cfg = load_json(self.folder / "config.json", {})
        token_prices = cfg.get("token_prices") or {}
        apply_prices(token_prices)
        apply_context(cfg.get("model_context"))
        apply_hidden(cfg.get("hidden_models"))
        basis = self.interaction_cost(events)
        return {"mode": self.ai_mode(), "model": self.model(), "cost_basis": basis, "limits": self.call_limits(cfg),
                "reviewer": self.reviewer_settings(cfg),
                "reasoning_effort": cfg["reasoning_effort"] if "reasoning_effort" in cfg else "low",
                "models": [{"id": model, "input_usd_per_1m": round(rates[0] * 1000, 4), "output_usd_per_1m": round(rates[1] * 1000, 4),
                            "per_100_usd": basis["per_100_usd"].get(model), "per_100_eur": basis["per_100_eur"].get(model),
                            "builtin": model in BUILTIN_PRICES, "edited": model in token_prices,
                            "context_tokens": context_of(model),
                            "context_known": model in BUILTIN_CONTEXT or model in (cfg.get("model_context") or {}),
                            "hidden": model in HIDDEN["models"]}
                           for model, rates in PRICE_PER_1K_USD.items()]}

    def call_limits(self, cfg=None):
        """29/09, Oficina: how big one call to the AI may be — a share of the model's context (50% by default) and at most
        so many emails (5, as before) —, so a batch never gets near the limit, where answers get worse."""
        limits = (cfg if cfg is not None else load_json(self.folder / "config.json", {})).get("call_limits") or {}
        return {"context_share": limits.get("context_share", CONTEXT_SHARE), "batch_emails": limits.get("batch_emails", BATCH_EMAILS)}

    def voice_signature(self):
        """02/10: the signature the program puts under every AI draft (Voz e estilo), one or more lines."""
        return str(((load_json(self.folder / "voice.json", {}).get("style") or {}).get("signature") or {}).get("text") or "")

    def auto_read_settings(self, cfg=None):
        """06/10, Settings: Emails reads the mailbox by itself when it is opened and there was no read yet, or the last one
        is more than «minutes» old (10 by default); on unless switched off."""
        cfg = cfg if cfg is not None else load_json(self.folder / "config.json", {})
        auto = cfg.get("auto_read") or {}
        minutes = auto.get("minutes")
        return {"on": auto.get("on") is not False,
                "minutes": minutes if isinstance(minutes, int) and 1 <= minutes <= 720 else AUTO_READ_MINUTES}

    def set_auto_read(self, on, minutes):
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            raise ValueError("Os minutos têm de ser um número inteiro.") from None
        if not 1 <= minutes <= 720:
            raise ValueError("Os minutos vão de 1 a 720.")
        with locked(self.folder):
            cfg = load_json(self.folder / "config.json", {})
            cfg["auto_read"] = {"on": bool(on), "minutes": minutes}
            save_json(self.folder / "config.json", cfg)
            self.log("auto_read_set", on=bool(on), minutes=minutes)
        return self.auto_read_settings()

    def reviewer_settings(self, cfg=None):
        """30/09, Oficina: the evaluator's model (stronger than the one that writes) and whether it reviews the real
        drafts by itself after «Gerar respostas» (02/10: off by default — the owner runs it with «Rever os selecionados»)."""
        cfg = cfg if cfg is not None else load_json(self.folder / "config.json", {})
        reviewer = cfg.get("reviewer") or {}
        model = reviewer.get("model")
        # 02/10: gpt-6-sol by default, the strongest of those on offer (gpt-4o left the list)
        return {"model": model if model in models() else next((m for m in ("gpt-6-sol", "gpt-5.6-terra", "gpt-4o")
                                                               if m in models()), self.model(cfg)),
                "auto": reviewer.get("auto") is True}  # 02/10: only when the owner asks, unless switched on

    def set_reviewer(self, model, auto):
        self.model()  # the Oficina's models too
        if model not in models():
            raise ValueError("Modelo desconhecido para o avaliador.")
        with locked(self.folder):
            cfg = load_json(self.folder / "config.json", {})
            cfg["reviewer"] = {"model": model, "auto": bool(auto)}
            save_json(self.folder / "config.json", cfg)
            self.log("reviewer_set", model=model, auto=bool(auto))
        return self.ai_settings()

    def review_drafts(self, property_ref, ids):
        """30/09: the draft reviewer — the evaluator marks these drafts (the conversation and the property's rules, no
        hidden truth) and each one keeps its review, valid while its text is the one reviewed. Up to 5 per call."""
        profiles = self.profiles()
        ref = self.pick(profiles, property_ref)
        current = next(queue for queue in self.pending(ref)["properties"] if queue["property_ref"] == ref)
        chosen = [email for email in current["emails"] if email["id"] in set(ids)
                  and len(str(email.get("reply_text") or "").strip()) >= REVIEW_MIN_TEXT]
        if not chosen:
            return {"reviewed": 0, "cost_usd": 0.0}
        self.require_fuel(ref)
        cfg = self.config()
        model = self.reviewer_settings(cfg)["model"]
        key = openai_api_key(self.folder, cfg["account"])
        found, cost = {}, 0.0
        moment = datetime.now().astimezone()
        batches = [chosen[start:start + 5] for start in range(0, len(chosen), 5)]
        prompts = []
        for batch in batches:
            items = []
            for email in batch:
                turns = sorted(email.get("history") or [], key=lambda turn: str(turn.get("ts") or turn.get("at") or ""))
                message = (email.get("customer") or {}).get("message")
                if message and not any(turn.get("text") == message for turn in turns):
                    turns.append({"who": "cliente", "text": message})
                items.append({"id": email["id"], "turns": turns, "reply": email["reply_text"]})
            prompts.append(evaluation_prompt(current["instructions"], items, hidden=False, now=moment))
        # 02/10: the reviews at the same time, as the replies themselves (api.run_parallel)
        from .api import run_parallel
        outcomes = run_parallel(lambda prompt_text: complete(key, model, prompt_text), prompts)
        if outcomes and all(isinstance(outcome, Exception) for outcome in outcomes):
            raise outcomes[0]
        for batch, outcome in zip(batches, outcomes):
            if isinstance(outcome, Exception):
                continue
            answer, usage = outcome
            part = estimate_cost_usd(model, usage.get("prompt_tokens"), usage.get("completion_tokens"))
            cost += part
            self.log("openai_usage", model=model, **usage, reference=ref, cost_usd=round(part, 6), purpose="review")
            found.update(parse_evaluations(answer, [email["id"] for email in batch]))
        texts = {email["id"]: email["reply_text"] for email in chosen}
        with locked(self.folder, wait=SHORT_WAIT):
            data = self.load(ref)
            for item in data["emails"]:
                review = found.get(item["id"])
                # only while the draft is the text that was read
                if review and text_hash(item.get("reply_text")) == text_hash(texts.get(item["id"])):
                    item["review"] = {**review, "hash": text_hash(item["reply_text"]), "model": model, "at": now()}
            self.save(data, ref)
        self.log("drafts_reviewed", reference=ref, count=len(found))
        return {"reviewed": len(found), "cost_usd": round(cost, 6)}

    def set_hidden(self, model, hidden):
        """02/10, Oficina: take a model off the list on offer (it keeps its price, for the old costs), or put it back."""
        self.model()
        if model not in PRICE_PER_1K_USD:
            raise ValueError("Modelo desconhecido.")
        with locked(self.folder):
            cfg = load_json(self.folder / "config.json", {})
            current = set(HIDDEN_DEFAULT_OF(cfg))
            current = current | {model} if hidden else current - {model}
            if hidden and model in (cfg.get("openai_model"), (cfg.get("reviewer") or {}).get("model")):
                raise ValueError("É o motor (ou o avaliador) em uso: escolhe outro antes de o tirar da lista.")
            cfg["hidden_models"] = sorted(current)
            save_json(self.folder / "config.json", cfg)
            self.log("model_hidden", model=model, hidden=bool(hidden))
        return self.ai_settings()

    def set_effort(self, effort):
        """02/10, Oficina: the reasoning effort for every call (none, minimal, low, medium, high), or "" for each model's own."""
        if effort not in ("", *EFFORTS):
            raise ValueError("Esforço inválido: nenhum, mínimo, baixo, médio, alto ou o do modelo.")
        with locked(self.folder):
            cfg = load_json(self.folder / "config.json", {})
            cfg["reasoning_effort"] = effort
            save_json(self.folder / "config.json", cfg)
            self.log("reasoning_effort_set", effort=effort or "modelo")
        apply_effort(effort)
        return self.ai_settings()

    def set_call_limits(self, context_share, batch_emails):
        if (isinstance(context_share, bool) or not isinstance(context_share, int) or not 10 <= context_share <= 90
                or isinstance(batch_emails, bool) or not isinstance(batch_emails, int) or not 1 <= batch_emails <= 10):
            raise ValueError("O contexto vai de 10 a 90% e os emails por chamada de 1 a 10.")
        with locked(self.folder):
            cfg = load_json(self.folder / "config.json", {})
            cfg["call_limits"] = {"context_share": context_share, "batch_emails": batch_emails}
            save_json(self.folder / "config.json", cfg)
            self.log("call_limits_set", context_share=context_share, batch_emails=batch_emails)
        return self.ai_settings()

    def set_context(self, model, tokens):
        """A model's context window, in tokens, as OpenAI announces it; 0 puts the default back."""
        model = " ".join(str(model or "").split())
        self.model()  # the Oficina's models too
        if model not in PRICE_PER_1K_USD:  # hidden ones included: their numbers stay right
            raise ValueError("Modelo desconhecido.")
        if isinstance(tokens, bool) or not isinstance(tokens, int) or not (tokens == 0 or 4000 <= tokens <= 10_000_000):
            raise ValueError("O contexto é um número de tokens, de 4.000 a 10.000.000 (0 para o valor de partida).")
        with locked(self.folder):
            cfg = load_json(self.folder / "config.json", {})
            context = dict(cfg.get("model_context") or {})
            if tokens:
                context[model] = tokens
            else:
                context.pop(model, None)
            cfg["model_context"] = context
            save_json(self.folder / "config.json", cfg)
            self.log("model_context_set", model=model, tokens=tokens)
        return self.ai_settings()

    def set_price(self, model, input_usd_per_1m=None, output_usd_per_1m=None, reset=False):
        """29/09, Oficina: a model's price per 1M tokens (input, output), kept in config.json "token_prices" — one more
        model when it is new. reset: back to the table's own price, or out of the list if it was the Oficina's."""
        model = " ".join(str(model or "").split())
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}", model):
            raise ValueError("Indica o nome do modelo, como a OpenAI o escreve (ex.: gpt-4o-mini).")
        with locked(self.folder):
            cfg = load_json(self.folder / "config.json", {})
            prices = dict(cfg.get("token_prices") or {})
            if reset:
                prices.pop(model, None)
                if model not in BUILTIN_PRICES and cfg.get("openai_model") == model:
                    raise ValueError("É o motor em uso: escolhe outro antes de o tirar da lista.")
            else:
                try:
                    values = [float(str(value).replace(",", ".")) for value in (input_usd_per_1m, output_usd_per_1m)]
                except (TypeError, ValueError):
                    raise ValueError("Indica os dois preços em dólares por 1M tokens (ex.: 0.15 e 0.60).") from None
                if not all(0 < value <= 1000 for value in values):
                    raise ValueError("Os preços têm de estar entre 0 e 1000 US$ por 1M tokens.")
                prices[model] = {"input_usd_per_1m": values[0], "output_usd_per_1m": values[1]}
            cfg["token_prices"] = prices
            save_json(self.folder / "config.json", cfg)
            self.log("token_price_set", model=model, reset=bool(reset))
        return self.ai_settings()

    def extract_listing(self, text, url=None):
        """«Extrair com a API»: the listing's text, pasted by the owner, becomes the fields they review. Charged to
        the property it names when that one already exists (its tank); a new property's first call is unattributed."""
        text = str(text or "").strip()
        if len(text) < 40:
            raise ValueError("Cola o texto do anúncio: abre-o no browser, seleciona tudo (⌘A), copia e cola aqui.")
        cfg = self.config()
        if not has_openai_api_key(self.folder, cfg["account"]):
            raise ValueError("Sem chave da OpenAI: guarda-a com mac/openai_key.command para usar a API.")
        url = str(url or "").strip() or None
        model = self.model(cfg)
        answer, usage = complete(openai_api_key(self.folder, cfg["account"]), model, listing_text_prompt(text, url))
        fields = parse_listing(answer)
        if url and not fields.get("listing_url"):
            fields = parse_listing(json.dumps({**fields, "listing_url": url}))
        known = fields.get("reference") in load_profiles(self.folder, cfg["account"])
        self.log("openai_usage", model=model, **usage, **({"reference": fields["reference"]} if known else {}),
                 cost_usd=round(estimate_cost_usd(model, **{k: usage[k] for k in ("prompt_tokens", "completion_tokens")}), 6))
        return {"fields": fields, "tokens": usage}

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

    # ===== The notice board (02/10): the system's important messages for the owner, on the Painel. Each one once (by
    # its key), with when, which property and where to go; read by the owner. 04/10: no longer archived by hand — while
    # what it says is true, it stays; it leaves by itself once over (the customer answered, the tank filled, a read or a
    # backup that worked, the customer moved on), the green and grey news after a week. The owner may pin a short note.

    def notify(self, key, text, ref=None, level="warn", tab=None, mark=None):
        """Puts a message on the board, once per key while the last one is on it; never fails what the caller was doing.
        04/10: mark, a post-it already coloured (NOTICE_MARKS), still unread."""
        try:
            with locked(self.folder, "notices", wait=SHORT_WAIT):
                board = load_notices(self.folder)
                if any(notice.get("key") == key and not notice.get("over") for notice in board["notices"]):
                    return False
                board["notices"].append({"id": secrets.token_hex(6), "key": key, "at": now(), "ref": ref,
                                         "level": level if level in NOTICE_LEVELS else "warn", "text": text[:600],
                                         "tab": tab, "read": False, "archived": False,
                                         **({"mark": mark, "mark_at": now()} if mark in NOTICE_MARKS else {})})
                self.trim_notices(board)
                save_notices(self.folder, board)
                return True
        except Exception:
            return False

    @staticmethod
    def trim_notices(board):
        """Keeps NOTICES_KEPT: the oldest finished ones go first, then the oldest of all."""
        extra = len(board["notices"]) - NOTICES_KEPT
        if extra > 0:
            finished = {id(notice) for notice in board["notices"] if notice.get("over") or notice.get("archived")}
            drop = set()
            for notice in board["notices"]:
                if len(drop) == extra:
                    break
                if id(notice) in finished:
                    drop.add(id(notice))
            board["notices"] = [notice for notice in board["notices"] if id(notice) not in drop]
            del board["notices"][:-NOTICES_KEPT]

    def clear_notices(self, prefix):
        """04/10: what the notices of this kind said is over (a read or a backup that worked): they leave the board."""
        try:
            with locked(self.folder, "notices", wait=SHORT_WAIT):
                board = load_notices(self.folder)
                ended = [notice for notice in board["notices"]
                         if str(notice.get("key") or "").startswith(prefix) and not notice.get("over")]
                for notice in ended:
                    notice["over"] = now()
                if ended:
                    save_notices(self.folder, board)
        except Exception:
            pass

    def notice_over(self, notice, board, queues):
        """04/10: whether what a notice says is no longer true, worked out from the data. queues: a cache by property."""
        key, ref = str(notice.get("key") or ""), notice.get("ref")
        if notice.get("level") in ("ok", "info"):
            try:
                age = datetime.now(timezone.utc) - datetime.fromisoformat(str(notice.get("at")))
            except (TypeError, ValueError):
                return False
            return age >= timedelta(days=NOTICE_EVENT_DAYS)
        if not ref:
            return False
        if ref not in queues:
            try:
                queues[ref] = self.load(ref) if self.queue_path(ref).exists() else None
            except Exception:
                queues[ref] = None
        data = queues[ref]
        if data is None:
            return key.startswith(("espera-", "alerta-", "shortlist-", "interacao-"))  # the property is gone
        if key.startswith("espera-"):  # the latest one says it all; over when no one waits that long any more
            newer = any(str(other.get("key") or "").startswith(f"espera-{ref}-") and not other.get("over")
                        and str(other.get("at")) > str(notice.get("at")) for other in board["notices"])
            return newer or not self.waiting_customers(data)
        if key.startswith(f"alerta-{ref}-"):  # the flagged message was answered (or left the queue)
            return all(item.get("id") != key[len(f"alerta-{ref}-"):] for item in data["emails"])
        if key.startswith(f"shortlist-{ref}-"):
            wrote = key[len(f"shortlist-{ref}-"):]
            return all(wrote not in (item.get("id"), item.get("gmail_message_id"), item.get("message_id"))
                       for item in data["emails"])
        if key.startswith(f"interacao-{CONCLUSIVE_AT}-{ref}-"):  # the owner stepped in, or the customer moved on
            digest = key.rsplit("-", 1)[-1]
            for email, conversation in data.get("conversations", {}).items():
                if hashlib.sha256(email.encode()).hexdigest()[:8] == digest:
                    today = date.today().isoformat()
                    return (conversation.get("stage", 0) != CONCLUSIVE_AT or bool(conversation.get("ignored"))
                            or shut_out(conversation) or bool(conversation.get("closed_at") or conversation.get("selection"))
                            or any(slot["customer"] == email and slot["at"][:10] >= today
                                   for slot in load_visits(self.folder, ref)["slots"]))
            return True
        if key.startswith((f"deposito-vazio-{ref}-", f"deposito-reserva-{ref}-")):  # filled again
            try:
                fuel = self.api_fuel(ref)
            except Exception:
                return False
            empty = key.startswith("deposito-vazio-")
            filled = key[len(f"deposito-{'vazio' if empty else 'reserva'}-{ref}-"):]
            if not fuel["configured"] or str(fuel["filled_at"]) != filled:
                return True
            return not fuel["empty"] if empty else (fuel["empty"] or not fuel["reserve"])
        return False

    def mark_documents(self, ref, found):
        """03/10: the documents a short-list customer sent (read by the AI from their words and the files' names) are
        marked as arrived in their selection; the owner can untick any in Contactos."""
        with locked(self.folder, wait=SHORT_WAIT):
            data = self.load(ref)
            by_id = {item["id"]: item for item in data["emails"]}
            marked = 0
            for entry in found:
                email = recipient_email(by_id.get(entry["id"]) or {})
                selection = (data.get("conversations", {}).get(email) or {}).get("selection")
                if not selection:
                    continue
                docs = selection.setdefault("docs", {})
                for code in entry["docs"]:
                    if code.startswith("fiador:") and not selection.get("fiador"):
                        continue
                    if not docs.get(code):
                        docs[code] = True
                        marked += 1
            if marked:
                self.save(data, ref)
                self.log("documents_marked", reference=ref, count=marked)
            return marked

    def flag_alerts(self, ref, alerts):
        """02/10: messages the AI flagged as important, dramatic or insulting — a warning on their card and a notice on
        the board, for the owner to read before answering (and maybe the grey or the black list)."""
        with locked(self.folder, wait=SHORT_WAIT):
            data = self.load(ref)
            by_id = {item["id"]: item for item in data["emails"]}
            flagged = []
            for alert in alerts:
                item = by_id.get(alert["id"])
                if item is not None:
                    item["ai_alert"] = {"kind": alert["kind"], "reason": alert["reason"], "at": now()}
                    flagged.append((item, alert))
            if flagged:
                self.save(data, ref)
        for item, alert in flagged:
            name = shown_name((item.get("recipient") or {}).get("name") or (item.get("customer") or {}).get("name"), "Um cliente")
            self.notify(f"alerta-{ref}-{item['id']}", f"{name} ({ref}): mensagem {ALERT_KINDS[alert['kind']]}"
                        + (f" — {alert['reason']}" if alert["reason"] else "") + ". Lê-a antes de responder; se for caso "
                        "disso, põe-o na lista cinzenta ou na lista negra.", ref,
                        "warn" if alert["kind"] == "importante" else "bad", "replies")

    @staticmethod
    def waiting_customers(data):
        """The emails of customers waiting WAITING_NOTICE_HOURS or more for our answer."""
        return [item for item in data["emails"] if item.get("kind") in ("lead", "follow_up") and not item.get("blocked")
                and not item.get("answered_directly") and (waited_hours(item) or 0) >= WAITING_NOTICE_HOURS]

    def waiting_notices(self, ref, data):
        """02/10, the board: customers waiting WAITING_NOTICE_HOURS or more for our answer, one notice per property a day."""
        waiting = self.waiting_customers(data)
        if not waiting:
            return
        names = [shown_name((item.get("recipient") or {}).get("name") or (item.get("customer") or {}).get("name"))
                 for item in waiting]
        days = int(max(waited_hours(item) for item in waiting) // 24)
        self.notify(f"espera-{ref}-{date.today().isoformat()}",
                    f"{len(waiting)} cliente(s) de {ref} à espera da nossa resposta há 3 dias ou mais (o mais antigo, há "
                    f"{days} dias): " + ", ".join(names[:8]) + ("…" if len(names) > 8 else "") + ".", ref, "warn", "replies")

    # ===== Calls (02/10): the portal's call notices («Chamada atendida / não respondida de um interessado»), read at
    # «Ler emails» or by «Procurar chamadas» (N days back), kept in chamadas.json and tied to a customer by the phone.

    def take_call(self, item, profiles):
        """One call notice, once: its property by the reference it names (or its listing code), when it names one."""
        found = parse_call(item)
        if not found:
            return False
        key = message_key(item)
        ref = found["ref"] if found["ref"] in profiles else next(
            (other for other, profile in profiles.items() if found["listing"]
             and str((profile.get("property") or {}).get("listing_id") or "") == found["listing"]), None)
        with locked(self.folder, "calls", wait=SHORT_WAIT):
            board = load_calls(self.folder)
            if any(call["id"] == key for call in board["calls"]):
                return False
            board["calls"].append({"id": key, **found, "property_ref": ref, "notice_at": item.get("date") or now()})
            save_calls(self.folder, board)
        self.log("call_noted", reference=ref, answered=found["answered"])
        return True

    def scan_calls(self, days):
        """«Procurar chamadas dos últimos N dias»: only the call notices, as far back as asked (a read goes back one day)."""
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
            raise ValueError("Indica quantos dias para trás: de 1 a 365.")
        cfg = self.config()
        profiles = self.profiles()
        known = {call["id"] for call in load_calls(self.folder)["calls"]}
        messages, scanned, _ = read_messages(
            cfg["account"], app_password(self.folder, cfg["account"]), "", (date.today() - timedelta(days=days)).isoformat(),
            (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat(), mailbox=cfg.get("mailbox", "all"),
            incoming_only=True, accept=lambda item: call_notice(item) and message_key(item) not in known)
        added = sum(1 for item in messages if self.take_call(item, profiles))
        self.log("calls_scanned", days=days, added=added)
        return {**self.calls_view(), "added": added, "scanned": scanned}

    def calls_view(self):
        """Every call, newest first, with the customer it belongs to when the phone is known (Contactos: their row, a
        lead's notice) — else «sem nome» — and the property: the one the notice names, else the customer's."""
        profiles = self.profiles()
        index = {}
        for (email, ref), row in load_contacts(self.folder).items():
            if row.get("telefone") and ref in profiles:
                index.setdefault(phone_key(row["telefone"]), []).append((ref, email, row.get("nome") or ""))
        shown = []
        for call in sorted(load_calls(self.folder)["calls"], key=lambda call: call.get("at") or "", reverse=True):
            matches = index.get(phone_key(call["phone"]), [])
            mine = [match for match in matches if match[0] == call.get("property_ref")] or matches
            who = mine[0] if mine else None
            digits = phone_key(call["phone"])
            international = "351" + digits if len(digits) == 9 else digits
            shown.append({**call, "property_ref": call.get("property_ref") or (who[0] if who else None),
                          "name": who[2] if who else "", "email": who[1] if who else "", "international": international,
                          "phone_shown": (f"+351 {digits[:3]} {digits[3:6]} {digits[6:]}" if len(digits) == 9 else "+" + digits)})
        return {"calls": shown}

    def owners_waiting(self):
        """04/10: the owners whose emails wait for our answer (their own, not ours to them), in the properties' queues
        and in the owners' inbox: email → {"name", "refs" (None: no property in the ARIA), "ids"}."""
        waiting = {}
        sources = [(ref, self.load(ref)) for ref in self.profiles() if self.queue_path(ref).exists()]
        for ref, data in [*sources, (None, self.load_caixa())]:
            for item in data.get("emails") or []:
                if item.get("kind") != "owner" or item.get("outbound") or item.get("reply_status") not in (None, "pending", "draft"):
                    continue
                email = recipient_email(item) or str((item.get("customer") or {}).get("email") or "").casefold()
                entry = waiting.setdefault(email, {"name": "", "refs": [], "ids": []})
                entry["name"] = entry["name"] or (item.get("customer") or {}).get("name") or (item.get("recipient") or {}).get("name") or ""
                if ref not in entry["refs"]:
                    entry["refs"].append(ref)
                entry["ids"].append(item.get("id"))
        return waiting

    def owners_notice(self, board, alert):
        """04/10: one red post-it (urgent) for every owner waiting for our answer, named with their properties; its
        list kept true. alert (at a read): an owner's new email brings it back unread and red. Over when none waits.
        Works on a board already loaded (and locked) by the caller; says whether it changed it."""
        try:
            waiting = self.owners_waiting()
        except Exception:
            return False
        notice = next((item for item in board["notices"] if item.get("key") == "proprietarios" and not item.get("over")), None)
        if not waiting:
            if notice:
                notice["over"] = now()
            return bool(notice)
        names = [f"{entry['name'] or email} ({', '.join(ref or 'sem imóvel na ARIA' for ref in entry['refs'])}"
                 + (f", {len(entry['ids'])} emails" if len(entry["ids"]) > 1 else "") + ")" for email, entry in waiting.items()]
        count = len(waiting)
        text = (f"{count} proprietário{'s' if count > 1 else ''} à espera da nossa resposta: " + "; ".join(names[:8])
                + ("…" if len(names) > 8 else "") + ". Responde em Proprietários.")[:600]
        ids = sorted(str(item_id) for entry in waiting.values() for item_id in entry["ids"])
        if notice is None:
            board["notices"].append({"id": secrets.token_hex(6), "key": "proprietarios", "at": now(), "ref": None,
                                     "level": "bad", "text": text, "tab": "owners", "read": False, "archived": False,
                                     "mark": "urgent", "mark_at": now(), "items": ids})
            self.trim_notices(board)
            return True
        if notice.get("text") == text and notice.get("items") == ids:
            return False
        if alert and set(ids) - set(notice.get("items") or []):
            notice.update(read=False, mark="urgent", mark_at=now())
        notice.update(text=text, items=ids)
        return True

    def update_owners_notice(self):
        """04/10, at the end of a read: the owners' post-it made or brought up to date (never fails the read)."""
        try:
            with locked(self.folder, "notices", wait=SHORT_WAIT):
                board = load_notices(self.folder)
                if self.owners_notice(board, alert=True):
                    save_notices(self.folder, board)
        except Exception:
            pass

    def notices(self):
        """The board as the page shows it: the ones still true, newest first, and how many are unread. 04/10: the ones
        whose news is over are marked so here, and leave (archived ones, from before 04/10, stay out); the owners'
        post-it lists those still waiting."""
        with locked(self.folder, "notices", wait=SHORT_WAIT):
            board, queues = load_notices(self.folder), {}
            ended = [notice for notice in board["notices"] if not notice.get("over") and not notice.get("archived")
                     and self.notice_over(notice, board, queues)]
            for notice in ended:
                notice["over"] = now()
            owners = self.owners_notice(board, alert=False)  # made here too: no need to wait for a read
            if ended or owners:
                save_notices(self.folder, board)
        shown = [notice for notice in reversed(board["notices"]) if not notice.get("archived") and not notice.get("over")]
        return {"notices": shown, "unread": sum(1 for notice in shown if not notice.get("read"))}

    def update_notices(self, ids, action, note=None, mark=None):
        """Marks notices read (ids None: every one shown); 04/10: or pins the owner's note on one (up to
        NOTICE_NOTE_CHARS; empty takes it off), or the owner's mark, the post-it's colour (NOTICE_MARKS; empty takes it
        off; a marked one is read). No archiving: a notice leaves when what it says is over."""
        if action not in ("read", "note", "mark"):
            raise ValueError("Ação desconhecida no quadro de avisos.")
        if action == "note" and (not ids or len(ids) != 1):
            raise ValueError("A nota vai num aviso de cada vez.")
        if action == "mark" and (not ids or len(ids) != 1):
            raise ValueError("A marca vai num aviso de cada vez.")
        mark = str(mark or "")
        if action == "mark" and mark and mark not in NOTICE_MARKS:
            raise ValueError("Marca desconhecida: urgente, não urgente ou tratado.")
        text = " ".join(str(note or "").split())
        if action == "note" and len(text) > NOTICE_NOTE_CHARS:
            raise ValueError(f"A nota tem no máximo {NOTICE_NOTE_CHARS} caracteres.")
        with locked(self.folder, "notices", wait=SHORT_WAIT):
            board = load_notices(self.folder)
            chosen = None if ids is None else {str(key) for key in ids}
            found = False
            for notice in board["notices"]:
                if chosen is None or notice.get("id") in chosen:
                    found = True
                    notice["read"] = True
                    if action == "note" and text:
                        notice["note"], notice["note_at"] = text, now()
                    elif action == "note":
                        notice.pop("note", None)
                        notice.pop("note_at", None)
                    elif action == "mark" and mark:
                        notice["mark"], notice["mark_at"] = mark, now()
                    elif action == "mark":
                        notice.pop("mark", None)
                        notice.pop("mark_at", None)
            if action in ("note", "mark") and not found:
                raise ValueError("Esse aviso já não está no quadro.")
            save_notices(self.folder, board)
        return self.notices()

    def log(self, event, **fields):
        # No bodies, passwords, OAuth tokens, subjects or recipient addresses in logs.
        folder = self.folder / "logs"
        folder.mkdir(mode=0o700, exist_ok=True)
        import os
        fd = os.open(folder / "events.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as stream:
            stream.write(json.dumps({"at": now(), "event": event, **fields}) + "\n")
        if event == "openai_usage" and fields.get("reference"):
            self.tank_notice(fields["reference"])

    def tank_notice(self, ref):
        """02/10, the board: a property's API tank in the reserve, or empty (once per fill)."""
        try:
            fuel = self.api_fuel(ref)
        except Exception:
            return
        if not fuel["configured"] or not (fuel["reserve"] or fuel["empty"]):
            return
        left = f"{max(fuel['remaining_eur'], 0):.2f}".replace(".", ",")
        if fuel["empty"]:
            self.notify(f"deposito-vazio-{ref}-{fuel['filled_at']}", f"O depósito da API de {ref} está vazio: a API parou "
                        "neste imóvel até o encheres (Painel → Depósitos).", ref, "bad", "dashboard")
        else:
            self.notify(f"deposito-reserva-{ref}-{fuel['filled_at']}", f"O depósito da API de {ref} está na reserva: "
                        f"restam {left} €.", ref, "watch", "dashboard")

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
        signature = (((voice or {}).get("style") or {}).get("signature") or {})
        signature = "" if signature.get("translate") else signature.get("text") or ""
        house = any("🏠" in part.get("text", "") for part in (voice or {}).get("_knowledge") or [])
        emails = []
        for item in data["emails"]:
            email = customer(item)
            # 27/09: no Reply-To with the customer's email in the notice is common on Idealista: no warning about it
            warnings = [warning for warning in item.get("warnings", [])
                        if not warning.startswith("Sem Reply-To: o destinatário é o email do corpo")]
            if email and counts[email] > 1:
                warnings.append("Há outro email pendente deste cliente neste imóvel; evita respostas repetidas.")
            if item.get("kind") == "owner":
                # 02/10: the owner's email (the Proprietários tab): their own conversation, no customer step
                talk = (data.get("owner_conversations") or {}).get(email) or {}
                emails.append({key: item.get(key) for key in VIEW_FIELDS} | {
                    "owner": True, "outbound": bool(item.get("outbound")), "new_subject": item.get("new_subject"),
                    "interaction": None, "warnings": list(item.get("warnings") or []), "phase": None,
                    "phone_only": False, "closing_reply": False, "conclusive_reply": False, "farewell": False,
                    "ficha": None, "ficha_summary": None, "qualifying_limit": False, "booked_at": None,
                    "draft_checks": draft_checks(item.get("reply_text"), signature, False, None),
                    "review_fresh": False, "answered_direct": False, "recipient_editable": False,
                    "conversation": list(talk.get("history") or [])})
                continue
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
            if missing and not qualifying and (item.get("kind") in ("visit_proposal", "visit_reminder") or interaction == 4):
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
            # 27/09: a customer's own email once their visit is booked, or after they visited: its own prompt, not «5.ª»
            check = conversation.get("visit_check") or {}
            selection = conversation.get("selection") or {}
            phase = (None if item.get("kind") not in ("lead", "follow_up") or item.get("survey_reply") else
                     # 03/10: on the short list, their reply asks for the documents (or says what came): over the rest
                     "shortlist" if selection.get("status") in SELECTION_STATES else
                     None if item.get("kind") != "follow_up" else
                     "visited" if check.get("attended") is True else "booked" if email in booked else None)
            # 27/09: a portal notice with no email of the customer's (blocked for the email) but a phone: its reply is
            # still written, to be sent by WhatsApp or SMS
            phone_only = bool(item.get("blocked") and not item.get("recipient") and item.get("kind") == "lead"
                              and (item.get("customer") or {}).get("phone"))
            chosen = (conversation.get("selection") or {}).get("status")
            if chosen in SELECTION_STATES and item.get("kind") in ("lead", "follow_up"):
                warnings.append(f"Cliente na short list ({SELECTION_STATES[chosen]}): é urgente, responde quanto antes.")
            if item.get("ai_alert"):  # 02/10: the AI flagged it for the owner (also on the notice board)
                alert = item["ai_alert"]
                warnings.append(f"A IA assinalou esta mensagem como {ALERT_KINDS.get(alert.get('kind'), 'importante')}"
                                + (f": {alert['reason']}" if alert.get("reason") else "") + ". Lê-a antes de responder.")
            # 02/10: a customer's own email after the 4th, with no visit booked: the 5th to the 7th wait for the owner
            # (the grey list, if it makes sense), the 8th asks them to step in, and from the 9th on the closing
            later = bool(email and phase is None and item.get("kind") in ("lead", "follow_up") and not item.get("survey_reply"))
            closing_reply = later and interaction >= CLOSING_FROM or bool(item.get("farewell"))
            if later and 5 <= interaction < CONCLUSIVE_AT:
                warnings.append(f"{interaction}.ª interação sem visita marcada: a IA responde só ao que perguntou e "
                                "aguarda por ti. Se não fizer sentido continuar, põe-no na lista cinzenta.")
            if later and interaction == CONCLUSIVE_AT:
                warnings.append(f"{CONCLUSIVE_AT}.ª interação sem visita marcada: a resposta é conclusiva e a próxima é o "
                                "fecho. Precisa da tua intervenção: lista cinzenta, propor-lhe uma visita ou deixar seguir.")
            emails.append({key: item.get(key) for key in VIEW_FIELDS} | {
                "interaction": interaction if email else None, "warnings": warnings, "phase": phase, "phone_only": phone_only,
                "closing_reply": closing_reply, "conclusive_reply": later and interaction == CONCLUSIVE_AT and not closing_reply,
                "farewell": bool(item.get("farewell")),
                "known_name": conversation.get("name") or "",  # 03/10: for taking their surnames out of the AI's texts
                # 03/10: the short list's documents: asked yet, what is still missing, and whether there is a guarantor
                "docs_requested": bool(selection.get("docs_requested_at")), "fiador": bool(selection.get("fiador")),
                "docs_missing": documents_summary(selection)["missing"] if phase == "shortlist" else [],
                "booked_at": ((visits or {}).get("booked_at") or {}).get(email) if phase == "booked" else None,
                "ficha": ficha, "ficha_summary": ficha_summary(ficha) if ref else None, "qualifying_limit": limit,
                "draft_checks": draft_checks(item.get("reply_text"), signature, house, item.get("visit_slot")),
                # 30/09: the reviewer's marks hold only for the text it read
                "review_fresh": bool(item.get("review")) and (item.get("review") or {}).get("hash") == text_hash(item.get("reply_text")),
                "answered_direct": bool(item.get("answered_directly")),  # 30/09: greyed out in the page, not ticked
                # A portal notice without a (valid) Reply-To: the owner may set or correct the recipient (26/09).
                "recipient_editable": bool(ref and item.get("kind") == "lead" and (not item.get("reply_to") or item.get("blocked"))
                                           and item.get("reply_status") in (None, "pending", "draft")),
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
                  "read_from": None if data.get("last_read_at") else (
                      data.get("read_from") or (date.today() - timedelta(days=FIRST_READ_DAYS)).isoformat()),
                  "instructions": instructions(profile, voice, visits), "emails": emails, "active": active,
                  "inactive": not property_active(profile),
                  # 04/10: how many «Escrever a todos» reaches, for each choice
                  "write_all": {key: len(value) for key, value in write_all_targets(data).items()} if ref else None}
        if added is not None:
            result["added"] = added
        return result

    def pending(self, property_ref=None):
        with locked(self.folder, wait=SHORT_WAIT):
            profiles = self.profiles()
            if not profiles:
                self.pick(profiles, property_ref)
                data = self.load()
                return {"revision": data["revision"], "account": data["account"],
                        "emails": data["emails"], "last_read_at": data.get("last_read_at")}
            refs = [self.pick(profiles, property_ref)] if property_ref else list(profiles)
            voice = load_voice(self.folder)
            return {"account": self.config()["account"],
                    "properties": [self.property_view(ref, profiles[ref], self.load(ref), voice) for ref in refs],
                    "owners": self.owners_view(profiles)}  # 03/10: the Proprietários tab

    def read(self, days=None):
        """Brings the new emails, each property from the day before its last read (27/09: no more «Dias para trás»
        in the page). A property never read goes back to the day chosen when it was created, else FIRST_READ_DAYS.
        days (terminal, MCP): reach back at least that far this time, in every property."""
        if days is not None and (isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365):
            raise ValueError("Indica os dias para trás: um número de 1 a 365.")
        self.reading.clear()
        self.reading.update(stage="connect")  # 02/10: what the read is doing, for the page (api read/progress)
        try:
            result = self.read_now(days)
            self.clear_notices("leitura-")  # 04/10: a read that worked: the failed read's notice is over
            return result
        except Exception as exc:
            if not isinstance(exc, RuntimeError):  # «another operation is running» is no failure
                message = " ".join(str(exc).split())[:300] or type(exc).__name__
                self.notify(f"leitura-{date.today().isoformat()}-{hashlib.sha256(message.encode()).hexdigest()[:8]}",
                            f"A leitura do Gmail falhou: {message}", None, "bad", "replies")
            raise
        finally:
            self.reading.clear()

    def read_now(self, days):
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
            # 02/10: each property's owner (its owner_email): their emails are not a customer's — a queue of their own
            owners = self.owner_index(profiles)
            caixa = self.load_caixa()  # 03/10: the owners with no property
            for owner_email, owner_refs in owners.items():
                for owner_ref in owner_refs:
                    self.adopt_owner(owner_ref, queues[owner_ref], owner_email)
            start_at = now()
            today = datetime.now(timezone.utc).date()
            starts = {}
            for ref, data in queues.items():
                if data.get("last_read_at"):
                    # One-day overlap handles date boundaries; IDs remove duplicates.
                    since = datetime.fromisoformat(data["last_read_at"]).date() - timedelta(days=1)
                else:
                    since = (date.fromisoformat(data["read_from"]) if data.get("read_from")
                             else today - timedelta(days=FIRST_READ_DAYS))
                starts[ref] = min(since, today - timedelta(days=days)) if days is not None else since
            # One scan for all: a new property's first read widens it, so each email is kept only within the
            # window of its own property — the others never get back mail older than their last read.
            start = min(starts.values())
            known = {ref: {message_key(e) for e in data["emails"]} | {merged for e in data["emails"] for merged in e.get("merged_ids", [])}
                     | set(data["replied_message_ids"]) | set(data["dismissed_message_ids"]) for ref, data in queues.items()}
            seen = set().union(*known.values())
            known_calls = {call["id"] for call in load_calls(self.folder)["calls"]}

            def before(item, since):
                arrived = aware(item.get("date"))
                return arrived is not None and arrived.astimezone(timezone.utc).date() < since

            def accept(item):
                # Decided on headers: known IDs and, with profiles, mail outside their families are skipped.
                if message_key(item) in seen:
                    return False
                if not profiles:
                    return True
                if call_notice(item):  # 02/10: the portal's call notices (no property reference in the subject)
                    return message_key(item) not in known_calls
                owner_ref = self.owner_route(item, owners)
                if owner_ref == CAIXA:
                    return message_key(item) not in set(caixa.get("seen_ids") or [])
                if owner_ref:
                    return not before(item, starts[owner_ref])
                ref, kind, _ = route(item, profiles, queues)
                if kind is None or (ref in starts and before(item, starts[ref])):
                    return False
                # The owner may have answered them from Gmail later in this same scan (All Mail goes by arrival).
                people.update(address.casefold() for address in addresses(item.get("reply_to") or []))
                threads.update({item.get("thread_id")} - {None, ""})
                return True

            # The owner's own replies, written straight from Gmail: to someone we know, or in a thread we know.
            # Never one this page sent: its Message-ID is in the conversation already.
            outgoing = [] if profiles else None
            talks = [conversation for data in queues.values() for conversation in data.get("conversations", {}).values()]
            ours = {sent for conversation in talks for sent in conversation.get("sent_message_ids", [])}
            people = ({email for data in queues.values() for email in data.get("conversations", {})}
                      | {recipient_email(item) for data in queues.values() for item in data["emails"]
                         if item.get("kind") != "owner"}) - {""}
            threads = ({item.get("thread_id") for data in queues.values() for item in data["emails"]}
                       | {thread for conversation in talks for thread in conversation.get("thread_ids", [])}) - {None, ""}

            def accept_outgoing(item):
                recipients = {a.casefold() for a in addresses((item.get("to") or []) + (item.get("cc") or []))}
                return item.get("message_id") not in ours and bool(recipients & people or item.get("thread_id") in threads)

            messages, scanned, mailbox = read_messages(
                cfg["account"], app_password(self.folder, cfg["account"]),
                "" if profiles else cfg.get("subject_contains", ""), start.isoformat(),
                # 02/10: up to tomorrow (UTC), with a day to spare — Gmail's IMAP counts days in the account's own time
                # zone, so between 00:00 and 01:00 in Lisbon «today in UTC» left out the emails already dated the next
                # day (20 test notices sent at 00:14 never came in). The IDs keep a wider window from importing twice.
                (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat(),
                mailbox=cfg.get("mailbox", "all"), incoming_only=bool(profiles) or cfg.get("incoming_only", True),
                accept=accept, outgoing=outgoing, accept_outgoing=accept_outgoing,
                progress=lambda number, total, sender, subject: self.reading.update(
                    stage="read", number=number, total=total, sender=str(sender)[:60], subject=str(subject)[:90]))
            self.reading.update(stage="save")
            added, ambiguous, contacts, received = dict.fromkeys(refs, 0), 0, [], {}
            for item in messages:
                if profiles and call_notice(item):
                    self.take_call(item, profiles)  # 02/10: into chamadas.json, never the queue
                    continue
                owner_ref = self.owner_route(item, owners) if profiles else None
                if owner_ref == CAIXA:
                    if message_key(item) not in set(caixa.get("seen_ids") or []):
                        self.take_owner_email(None, caixa, item, {"property": {}, "reply": {}}, cfg["account"])
                        caixa.setdefault("seen_ids", []).append(message_key(item))
                    continue
                if owner_ref:
                    key = message_key(item)
                    if key not in known[owner_ref]:
                        self.take_owner_email(owner_ref, queues[owner_ref], item, profiles[owner_ref], cfg["account"])
                        known[owner_ref].add(key)
                    continue
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
                                         "fonte": CONTACT_SOURCE, "perfil": item.get("profile_url") or ""})
                    # Known by their email already, whether this message is a direct reply (follow_up) or
                    # another portal notice (lead) from someone we have written to before either way.
                    conversation = queues[ref]["conversations"].get(email) if email else None
                    if conversation is not None and (conversation.get("visit_check") or {}).get("thanks_sent_at"):
                        # An answer to the after-visit email: the survey and the visit sheet, kept on the customer.
                        survey = parse_survey(item["customer"].get("message") or item.get("body_text"))
                        if survey:
                            conversation["visit_survey"] = {**survey, "at": item.get("date") or now()}
                            # 26/09: the assistant thanks them (see ai.SURVEY_REPLY_RULE), and a bad mark is flagged.
                            item["survey_reply"] = {"alerts": survey_alerts(survey)}
                            item.setdefault("warnings", []).append(SURVEY_NOTICE)
                            if item["survey_reply"]["alerts"]:
                                item["warnings"].append("Atenção ao inquérito: " + "; ".join(item["survey_reply"]["alerts"])
                                                        + ". Lê o comentário antes de responder.")
                    selection = ((conversation or {}).get("selection") or {}).get("status")
                    if selection in SELECTION_STATES and not item.get("blocked"):
                        # 02/10: someone on the short list wrote: urgent, on the notice board at once
                        who = shown_name(item["customer"].get("name") or (conversation or {}).get("name"), "Um cliente")
                        self.notify(f"shortlist-{ref}-{key}", f"{who} ({ref}), na short list ({SELECTION_STATES[selection]}), "
                                    "escreveu: é urgente, responde quanto antes.", ref, "bad", "replies")
                    if conversation is not None:
                        # A snapshot of everything before this message: shown in "Email completo" and sent
                        # in the prompt, so the assistant (ChatGPT or the API) sees the whole exchange.
                        item["history"] = list(conversation.get("history") or [])
                        self.append_history(conversation, "cliente", item["customer"].get("message"),
                                            contact_day(item), item.get("date"))
                        conversation.pop("absent", None)  # 06/10: they wrote again: no longer absent
                        if conversation.get("inactive") and property_active(profiles[ref]):
                            conversation.pop("inactive")  # they wrote again: active again (26/09)
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
            direct = self.record_direct_replies(queues, outgoing, starts) if profiles else Counter()
            if profiles:
                for ref, data in queues.items():
                    contacts += self.repair_missing_reply_to(ref, data, profiles[ref], cfg["account"])
                    self.repair_surveys(data)
                    self.drop_empty_additions(data)
                    self.merge_pending(data)
            add_contacts(self.folder, contacts)
            for ref, data in queues.items():
                data["last_read_at"] = start_at
                data["stats"] = {"new_this_read": added[ref], "scanned": scanned, "mailbox": mailbox,
                                 "direct_replies": direct[ref]}
                if ref and voice_ok:
                    self.schedule_reminders(ref, data, voice_ok)
                    self.mark_inactive(ref, data)
                    self.schedule_visit_reminders(ref, data)
                self.save(data, ref)
                if ref:
                    self.waiting_notices(ref, data)
            # received: message ID → the day the customer's email arrived, so the dashboard still counts it
            # after it is answered or dismissed and leaves the queue. IDs and dates only, never an address.
            if profiles:
                self.save_caixa(caixa)
                self.update_owners_notice()  # 04/10: one red post-it with every owner waiting for our answer
                self.auto_backup()  # 02/10: once a day, at the first read (the queue is saved and still locked: a clean copy)
            self.log("read", added=sum(added.values()), ambiguous=ambiguous, direct=sum(direct.values()),
                     pending=sum(len(data["emails"]) for data in queues.values()), received=received)
            if not profiles:
                data = queues[None]
                return {"added": added[None], "revision": data["revision"], "emails": data["emails"]}
            voice = load_voice(self.folder)
            return {"scanned": scanned, "ambiguous": ambiguous, "direct": sum(direct.values()),
                    "properties": [self.property_view(ref, profiles[ref], queues[ref], voice, added[ref]) for ref in refs]}

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

    def record_direct_replies(self, queues, outgoing, starts=None):
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
        try:  # 03/10: the hidden mark of our own emails found in Sent (a rebuild): read back with the Mac's key
            mark_key = tag_key(self.folder, self.config()["account"])
        except Exception:
            mark_key = None
        ours = {sent for data in queues.values()
                for conversation in [*data["conversations"].values(), *data.get("owner_conversations", {}).values()]
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
                return (item.get("kind") not in PROGRAM_KINDS | {"owner"} and bool(recipient_email(item))
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
            if starts and ref in starts and sent_at.astimezone(timezone.utc).date() < starts[ref]:
                continue  # older than this property's window: a new property's first read reached that far
            created = email not in data["conversations"]
            conversation = data["conversations"].setdefault(email, {"stage": 0, "sent_message_ids": [], "thread_ids": []})
            mine = [item for item in data["emails"] if recipient_email(item) == email and item.get("kind") not in PROGRAM_KINDS]
            for item in mine:  # 06/10: the language chosen on the portal (its flag)
                if (item.get("customer") or {}).get("portal_lang"):
                    conversation.setdefault("portal_lang", item["customer"]["portal_lang"])
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
            # 05/10: an «Escrever mais» draft opened before this reply and still empty: what the owner had to add went in
            # Gmail, so it leaves the queue (one with a text of the owner's stays, for them to decide)
            stale = [item for item in data["emails"] if recipient_email(item) == email and item.get("kind") == "addition"
                     and not (item.get("reply_text") or "").strip() and not item.get("addition_note")
                     and item.get("reply_status") in (None, "pending")
                     and (aware(item.get("date")) or sent_at) <= sent_at]
            if stale:
                data["emails"] = [item for item in data["emails"] if not any(item is gone for gone in stale)]
            if answered:
                # The reply written in Gmail is that step of the conversation.
                conversation["stage"] = conversation.get("stage", 0) + 1
                name = next(((item.get("recipient") or {}).get("name") or (item.get("customer") or {}).get("name")
                             for item in answered
                             if (item.get("recipient") or {}).get("name") or (item.get("customer") or {}).get("name")), "")
                if name and not conversation.get("name"):
                    conversation["name"] = name
            fields = mark.read_header(message.get("aria"), mark_key) if message.get("aria") and mark_key else None
            if fields:  # 03/10: what our email was, as its mark says (our nth email, its kind, a visit, the short list)
                marks = conversation.setdefault("marks", [])
                if not any(entry.get("id") == key for entry in marks):
                    marks.append({"id": key, "at": sent_at.astimezone(timezone.utc).isoformat(), **fields})
                if str(fields.get("n") or "").isdigit():
                    conversation["stage"] = max(conversation.get("stage", 0), int(fields["n"]))
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
        with locked(self.folder, wait=SHORT_WAIT):
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
                item["ficha"] = ficha_update((conversation or {}).get("ficha") or item.get("ficha"), entry["ficha"])
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

    # ===== Owners (02/10): each property's owner (property.owner_email) is not a customer. Their emails go to a queue
    # of their own (kind "owner", answered in the Proprietários tab with a prompt of their own), and their conversation
    # to data["owner_conversations"]: never in the customers' cards, rounds, files, contacts or the Painel's numbers.

    def backup_settings(self, cfg=None):
        """Where the backups go and the last one there (name, size, when)."""
        cfg = cfg or self.config()
        folder = str(cfg.get("backup_folder") or "")
        copies = sorted(Path(folder).glob(BACKUP_PREFIX + "*.zip")) if folder and Path(folder).is_dir() else []
        last = copies[-1] if copies else None
        return {"folder": folder, "count": len(copies), "drives": self.drive_folders(),
                "last": {"file": last.name, "bytes": last.stat().st_size,
                         "at": datetime.fromtimestamp(last.stat().st_mtime, timezone.utc).isoformat()} if last else None}

    @staticmethod
    def drive_folders():
        """Google Drive for desktop on this Mac: its «My Drive» folders, with the ARIA-copias folder the backups would use."""
        base = Path.home() / "Library" / "CloudStorage"
        found = []
        for root in sorted(base.glob("GoogleDrive-*")) if base.is_dir() else []:
            mine = next((root / name for name in DRIVE_NAMES if (root / name).is_dir()), None)
            if mine:
                found.append({"account": root.name.split("-", 1)[1], "path": str(mine / "ARIA-copias")})
        return found

    def portal_view(self, cfg=None):
        """02/10, Oficina: the portal as it stands, its defaults and what each field is."""
        cfg = cfg or self.config()
        return {"fields": portals.merged(cfg.get("portal")), "defaults": portals.DEFAULT, "labels": portals.LABELS,
                "changed": sorted((cfg.get("portal") or {}).keys())}

    def save_portal(self, fields, reset=False):
        """02/10, Oficina: the portal's changes (only what differs from the defaults is kept); reset: the defaults back."""
        changes = {} if reset else portals.check(fields)
        with locked(self.folder, "config", wait=SHORT_WAIT):
            path = self.folder / "config.json"
            cfg = load_json(path, {})
            cfg["portal"] = changes
            save_json(path, cfg)
        self.log("portal_saved", changed=sorted(changes))
        return self.portal_view()

    @staticmethod
    def choose_folder():
        """02/10: «Escolher pasta…»: the Mac's own folder chooser, opened by the local server (the page cannot get a path
        from the browser). Its path, or ValueError when cancelled or not on a Mac."""
        if sys.platform != "darwin":
            raise ValueError("Escreve o caminho completo da pasta.")
        script = ['tell application "System Events"', "activate",
                  'POSIX path of (choose folder with prompt "Escolhe a pasta para as cópias de segurança da ARIA")', "end tell"]
        result = subprocess.run(["osascript", *[part for line in script for part in ("-e", line)]],
                                capture_output=True, text=True, timeout=600)
        path = result.stdout.strip()
        if result.returncode != 0 or not path:
            raise ValueError("Nenhuma pasta escolhida.")
        return path.rstrip("/") or "/"

    def set_backup_folder(self, folder, create=False):
        """The folder for the backups (a local path, e.g. one Google Drive syncs); empty: no backups. create: make the
        folder itself (only it: its parent must exist), as for Google Drive's ARIA-copias."""
        folder = str(folder or "").strip()
        if folder:
            path = Path(folder).expanduser()
            if create and path.is_absolute() and path.parent.is_dir():
                path.mkdir(exist_ok=True)
            if not path.is_absolute() or not path.is_dir():
                raise ValueError("Indica uma pasta que exista, com o caminho completo (por exemplo /Users/…/Google Drive/ARIA).")
            if path.resolve() == self.folder.resolve() or self.folder.resolve() in path.resolve().parents:
                raise ValueError("A pasta das cópias não pode ficar dentro da pasta de dados.")
            if not os.access(path, os.W_OK):
                raise ValueError("Não consigo escrever nessa pasta.")
            folder = str(path)
        with locked(self.folder, "config", wait=SHORT_WAIT):
            path = self.folder / "config.json"
            cfg = load_json(path, {})
            cfg["backup_folder"] = folder or None
            save_json(path, cfg)
        self.log("backup_folder_set", on=bool(folder))
        return self.backup_settings()

    def backup(self, moment=None):
        """One backup now: the data folder, zipped, without the keys or the lock and temporary files."""
        import zipfile
        folder = str(self.config().get("backup_folder") or "")
        if not folder or not Path(folder).is_dir():
            raise ValueError("Escolhe primeiro a pasta das cópias de segurança (Settings).")
        moment = moment or datetime.now()
        target = Path(folder) / f"{BACKUP_PREFIX}{moment:%Y-%m-%d-%H%M%S}.zip"
        partial = target.with_suffix(".zip.part")
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(self.folder.rglob("*")):
                relative = path.relative_to(self.folder)
                if (not path.is_file() or relative.parts[0] == "secrets"
                        or any(part.startswith(".") for part in relative.parts)):
                    continue
                archive.write(path, Path("data") / relative)
        partial.replace(target)  # nothing older is deleted: backups are only ever added
        self.log("backup_made", bytes=target.stat().st_size)
        self.clear_notices("copia-")  # 04/10: a backup that worked: a failed one's notice is over
        return self.backup_settings()

    def auto_backup(self):
        """At a read: one backup a day, if a folder was chosen; a failure goes to the notice board, never stops the read."""
        settings = self.backup_settings()
        if not settings["folder"]:
            return None
        last = settings["last"]
        if last and datetime.fromisoformat(last["at"]).astimezone().date() == date.today():
            return None
        try:
            return self.backup()
        except Exception as exc:
            self.notify(f"copia-{date.today().isoformat()}", f"A cópia de segurança de hoje falhou: {' '.join(str(exc).split())[:200]}",
                        None, "bad", "dashboard")
            return None

    def owner_index(self, profiles):
        """owner's email → the properties it owns (test properties never have a real owner); 03/10: the owners' list too,
        an owner with no property owning [] (their emails go to the owners' inbox)."""
        index = {email: [] for email in self.owners_list()}
        for ref, profile in profiles.items():
            email = str((profile.get("property") or {}).get("owner_email") or "").strip().casefold()
            if email and not profile.get("test"):
                index.setdefault(email, []).append(ref)
        return index

    @staticmethod
    def owner_route(item, owners):
        """The property an owner's email belongs to (its reference in the subject when they own several), or None."""
        if item.get("test"):
            return None
        senders = {address.casefold() for address in addresses(item.get("from") or [])}
        email = next((email for email in senders if email in owners), None)
        if email is None:
            return None
        refs = owners[email]
        if not refs:
            return CAIXA  # 03/10: an owner with no property in the ARIA: the owners' inbox
        return next((ref for ref in refs if has_token(item.get("subject", ""), ref)), refs[0])

    def take_owner_email(self, ref, data, item, profile, account):
        """One email from the owner, into the owner's queue with its conversation's history."""
        owners = {str(profile["property"].get("owner_email") or "").casefold()} if ref else set(self.owners_list())
        email = next(address for address in addresses(item.get("from") or []) if address.casefold() in owners)
        item.update(prepare(item, "follow_up", email.casefold(), profile, account), kind="owner")
        talk = data.setdefault("owner_conversations", {}).setdefault(email.casefold(), {"sent_message_ids": [],
                                                                                         "thread_ids": []})
        item["history"] = list(talk.get("history") or [])
        self.append_history(talk, "cliente", item["customer"].get("message"), contact_day(item), item.get("date"))
        if item["customer"].get("name"):
            talk["name"] = item["customer"]["name"]
        if item.get("thread_id") and item["thread_id"] not in talk["thread_ids"]:
            talk["thread_ids"].append(item["thread_id"])
        item.update(id=message_key(item), reply_text="", send_reply=False, reply_status="pending")
        data["emails"].append(item)

    def adopt_owner(self, ref, data, email):
        """What was taken for a customer's but is the owner's (their email set after it came in): their queue items,
        their conversation and their row in Contactos move to the owner's side. Nothing is lost."""
        email = email.casefold()
        moved = False
        for item in data["emails"]:
            senders = {address.casefold() for address in addresses(item.get("from") or [])}
            if item.get("kind") not in ("lead", "follow_up") or not (recipient_email(item) == email or email in senders):
                continue
            message = (item.get("customer") or {}).get("message")
            if email in senders and message:
                # 02/10: sent by the owner in a customer's Gmail thread, it was read as that customer's (an «ambiguous
                # conversation»): their words leave the customer's history, so the AI never reads them as the customer's
                for holder in [*data.get("conversations", {}).values(), *(other for other in data["emails"] if other is not item)]:
                    if holder.get("history"):
                        holder["history"] = [turn for turn in holder["history"]
                                             if not (turn.get("who") == "cliente" and turn.get("text") == message)]
                talk = data.setdefault("owner_conversations", {}).setdefault(email, {"sent_message_ids": [], "thread_ids": []})
                if not any(turn.get("text") == message for turn in talk.get("history") or []):
                    self.append_history(talk, "cliente", message, contact_day(item), item.get("date"))
            sender = next((entry for entry in item.get("from") or [] if str(entry.get("email") or "").casefold() == email), {})
            name = (item.get("customer") or {}).get("name") or sender.get("name") or ""
            item.update(kind="owner", recipient={"name": name, "email": email},
                        customer={**(item.get("customer") or {}), "email": email, "name": name})
            if str(item.get("blocked") or "").startswith("Conversa ambígua"):
                item["blocked"] = None
            moved = True
        if email in data.get("conversations", {}):
            talk = data["conversations"].pop(email)
            kept = data.setdefault("owner_conversations", {}).setdefault(email, {"sent_message_ids": [], "thread_ids": []})
            for key in ("sent_message_ids", "thread_ids"):
                kept[key] = list(dict.fromkeys(kept.get(key, []) + talk.get(key, [])))
            kept["history"] = sorted(kept.get("history", []) + talk.get("history", []),
                                     key=lambda turn: str(turn.get("ts") or turn.get("at") or ""))[-HISTORY_LIMIT:]
            kept.setdefault("name", talk.get("name") or "")
            moved = True
        contacts = load_contacts(self.folder)
        if (email, ref) in contacts:
            del contacts[(email, ref)]
            save_contacts(self.folder, contacts)
        return moved

    # ===== The owners' list and the inbox of those with no property (03/10): an owner is in the list with or without
    # properties; their emails never become a customer's. Those of an owner with no property in the ARIA go to
    # data/proprietarios/caixa.json, answered in the Proprietários tab like the others.

    def owners_list(self):
        """email → {"name"} — the owners' list (data/proprietarios/donos.json)."""
        owners = load_json(self.folder / OWNER_FOLDER / "donos.json", {}).get("owners")
        return {str(email).casefold(): value for email, value in (owners or {}).items()} if isinstance(owners, dict) else {}

    def add_owner(self, email, name=""):
        """An owner into the list (or their name updated), with or without properties."""
        email = " ".join(str(email or "").split())
        if not email or len(email) > 200 or not EMAIL.fullmatch(email):
            raise ValueError("O email do proprietário tem de ser um endereço de email.")
        if email.casefold() == self.config()["account"].casefold():
            raise ValueError("O email do proprietário não pode ser o desta conta.")
        path = self.folder / OWNER_FOLDER / "donos.json"
        with locked(self.folder, "owners", wait=SHORT_WAIT):
            data = load_json(path, {})
            owners = data.setdefault("owners", {})
            entry = owners.setdefault(email.casefold(), {"added_at": now()})
            if " ".join(str(name or "").split()):
                entry["name"] = " ".join(str(name).split())[:100]
            save_json(path, data)
        return email.casefold()

    def load_caixa(self):
        caixa = load_json(self.folder / OWNER_FOLDER / "caixa.json", None)
        return caixa if isinstance(caixa, dict) and isinstance(caixa.get("emails"), list) else {"emails": [], "seen_ids": []}

    def save_caixa(self, caixa):
        (self.folder / OWNER_FOLDER).mkdir(parents=True, exist_ok=True)
        save_json(self.folder / OWNER_FOLDER / "caixa.json", caixa)

    def owners_view(self, profiles=None):
        """The Proprietários tab: every owner (the list and the properties' owners), their properties, and the inbox's
        emails (those of owners with no property), as cards."""
        profiles = profiles if profiles is not None else self.profiles()
        index = self.owner_index(profiles)
        names = {email: (value.get("name") or "") for email, value in self.owners_list().items()}
        for ref in profiles:
            prop = profiles[ref].get("property") or {}
            if prop.get("owner_email") and prop.get("owner_name"):
                names.setdefault(str(prop["owner_email"]).casefold(), prop["owner_name"])
        caixa = self.load_caixa()
        talks = caixa.get("owner_conversations") or {}
        emails = [{**{key: item.get(key) for key in VIEW_FIELDS}, "owner": True, "outbound": bool(item.get("outbound")),
                   "new_subject": item.get("new_subject"), "property_ref": CAIXA, "warnings": list(item.get("warnings") or []),
                   "conversation": list((talks.get(recipient_email(item)) or {}).get("history") or [])} for item in caixa["emails"]]
        return {"owners": [{"email": email, "name": names.get(email) or "", "refs": refs} for email, refs in sorted(index.items())],
                "inbox": emails}

    def caixa_drafts(self, replies):
        """Drafts of the inbox's emails (owners with no property)."""
        with locked(self.folder, "owners", wait=SHORT_WAIT):
            caixa = self.load_caixa()
            by_id = {item["id"]: item for item in caixa["emails"]}
            saved = 0
            for reply in replies or []:
                item = by_id.get(reply.get("id"))
                if item is not None:
                    item.update(reply_text=str(reply.get("reply_text") or ""), reply_status="draft" if str(reply.get("reply_text") or "").strip() else "pending")
                    saved += 1
            self.save_caixa(caixa)
            return saved

    def caixa_preview(self, item_id):
        """Who it goes to, the subject, and the text's fingerprint the send must find unchanged."""
        caixa = self.load_caixa()
        item = next((entry for entry in caixa["emails"] if entry["id"] == item_id), None)
        if item is None or not str(item.get("reply_text") or "").strip():
            raise ValueError("Escreve primeiro a resposta.")
        email = recipient_email(item)
        if email not in self.owners_list():
            raise ValueError("Esse email já não está na lista de proprietários.")
        msg, recipient = build_reply(item, self.config()["account"], (load_voice(self.folder).get("style", {}).get("sender_name") or {}).get("text") or "",
                                     item.get("new_subject"))
        return {"to": recipient, "subject": str(msg["Subject"]), "check": text_hash(item["reply_text"])}

    def caixa_send(self, item_id, check, confirmed):
        """Sends one inbox email after its preview (the same text: check), with the hidden mark; the owner's conversation
        keeps it."""
        if confirmed is not True:
            raise ValueError("É necessária confirmação explícita.")
        cfg = self.config()
        with locked(self.folder, "owners", wait=SHORT_WAIT):
            caixa = self.load_caixa()
            item = next((entry for entry in caixa["emails"] if entry["id"] == item_id), None)
            if item is None or text_hash(item.get("reply_text")) != check:
                raise ValueError("A resposta mudou: revê-a e confirma de novo.")
            if recipient_email(item) not in self.owners_list():
                raise ValueError("Esse email já não está na lista de proprietários.")
            style = load_voice(self.folder).get("style", {})
            msg, recipient = build_reply(item, cfg["account"], (style.get("sender_name") or {}).get("text") or "", item.get("new_subject"))
            try:
                key = tag_key(self.folder, cfg["account"])
                fields = {"ref": "caixa", "n": len(((caixa.get("owner_conversations") or {}).get(recipient_email(item)) or {})
                                                   .get("sent_message_ids") or []) + 1, "k": "owner"}
                del msg["Message-ID"]
                msg["Message-ID"] = mark.message_id(fields, key)
                msg["X-ARIA"] = mark.header(fields, key)
            except Exception:
                pass  # without the mark's key the email still goes
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
                smtp.login(cfg["account"], app_password(self.folder, cfg["account"]))
                smtp.send_message(msg)
            caixa["emails"].remove(item)
            item["reply_message_id"] = str(msg["Message-ID"])
            self.advance(caixa, item)  # the owner's conversation (kind "owner")
            self.save_caixa(caixa)
        self.log("send", message_id=item_id, status="sent", kind="owner", reference=None)
        return {"status": "sent", "to": recipient}

    def caixa_dismiss(self, item_id):
        with locked(self.folder, "owners", wait=SHORT_WAIT):
            caixa = self.load_caixa()
            caixa["emails"] = [item for item in caixa["emails"] if item["id"] != item_id]
            self.save_caixa(caixa)

    def set_owner(self, property_ref, email, name=""):
        """02/10, Proprietários: a property's owner (email and name), set or changed there; the same owner may have several
        properties. An empty email takes the owner off. What came in from them as a customer moves to their side."""
        email = " ".join(str(email or "").split())
        name = " ".join(str(name or "").split())[:100]
        if email and (len(email) > 200 or not EMAIL.fullmatch(email)):
            raise ValueError("O email do proprietário tem de ser um endereço de email.")
        with locked(self.folder, wait=SHORT_WAIT):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            if not ref or profiles[ref].get("test"):
                raise ValueError("Escolhe um imóvel (o de teste não tem proprietário).")
            if email.casefold() == self.config()["account"].casefold():
                raise ValueError("O email do proprietário não pode ser o desta conta.")
            path = property_folder(self.folder, ref) / "profile.json"
            profile = load_json(path, None)
            profile["property"].update(owner_email=email or None, owner_name=name or None)
            save_json(path, profile)
            if email:
                self.add_owner(email, name)  # 03/10: the owners' list
            if email:
                data = self.load(ref)
                if self.adopt_owner(ref, data, email):
                    self.save(data, ref)
            self.log("owner_set", reference=ref, owner=bool(email))
            return ref

    def write_to_owner(self, property_ref, subject="", owner=None):
        """02/10, «Escrever ao proprietário»: a new email to them, without them writing first — a card of its own, to
        write by hand or with the AI, then reviewed and sent like a reply. 03/10: property_ref CAIXA + owner: to an owner
        with no property (the owners' inbox)."""
        if property_ref == CAIXA:
            email = str(owner or "").strip().casefold()
            owners = self.owners_list()
            if email not in owners:
                raise ValueError("Escolhe um proprietário da lista.")
            with locked(self.folder, "owners", wait=SHORT_WAIT):
                caixa = self.load_caixa()
                name = owners[email].get("name") or ""
                talk = (caixa.get("owner_conversations") or {}).get(email) or {}
                subject = " ".join(str(subject or "").split())[:150] or "Contacto da agência"
                key = f"proprietario-{secrets.token_hex(5)}"
                caixa["emails"].append({"id": key, "kind": "owner", "outbound": True, "new_subject": subject, "subject": subject,
                                        "date": now(), "recipient": {"name": name, "email": email},
                                        "customer": {"name": name, "email": email, "phone": None, "message": None},
                                        "history": list(talk.get("history") or []), "blocked": None, "warnings": [],
                                        "reply_text": "", "send_reply": False, "reply_status": "pending"})
                self.save_caixa(caixa)
            return {"property_ref": CAIXA, "id": key}
        with locked(self.folder, wait=SHORT_WAIT):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            prop = profiles[ref]["property"] if ref else {}
            email = str(prop.get("owner_email") or "").strip()
            if not email:
                raise ValueError("Este imóvel ainda não tem o email do proprietário: põe-no primeiro.")
            data = self.load(ref)
            talk = (data.get("owner_conversations") or {}).get(email.casefold()) or {}
            subject = " ".join(str(subject or "").split())[:150] or f"{prop.get('reference')} — {prop.get('description') or ''}".strip(" —")
            name = prop.get("owner_name") or talk.get("name") or ""
            key = f"proprietario-{secrets.token_hex(5)}"
            data["emails"].append({"id": key, "kind": "owner", "outbound": True, "new_subject": subject, "subject": subject,
                                   "date": now(), "recipient": {"name": name, "email": email},
                                   "customer": {"name": name, "email": email, "phone": None, "message": None},
                                   "history": list(talk.get("history") or []), "blocked": None, "warnings": [],
                                   "reply_text": "", "send_reply": False, "reply_status": "pending"})
            self.save(data, ref)
            self.log("owner_write", reference=ref)
            return {"property_ref": ref, "id": key}

    def owner_prompt_for(self, property_ref, ids, now=None, extra=""):
        """02/10: the prompt for the owner's emails chosen, and what parsing its answer needs (the emails, the revision)."""
        if property_ref == CAIXA:  # 03/10: an owner with no property in the ARIA
            items = [item for item in self.load_caixa()["emails"] if item["id"] in set(ids or [])]
            if not items:
                raise ValueError("Escolhe pelo menos um email do proprietário.")
            owner = recipient_email(items[0])
            profile = {"property": {"reference": "sem imóvel", "description": "um proprietário sem imóveis na ARIA"}}
            prompt = owner_prompt(profile, load_voice(self.folder), load_knowledge(self.folder / OWNER_FOLDER),
                                  "(este proprietário ainda não tem imóveis nesta pasta de dados)", items, now, extra,
                                  load_knowledge(owner_folder(self.folder, owner)))
            return CAIXA, prompt, {"emails": items}
        with locked(self.folder, wait=SHORT_WAIT):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            data = self.load(ref)
            items = [item for item in data["emails"] if item["id"] in set(ids or []) and item.get("kind") == "owner"]
            if not items:
                raise ValueError("Escolhe pelo menos um email do proprietário.")
            report = self.owner_report_text(self.owner_report(ref, profiles[ref], data), date.today().isoformat())
            owner = profiles[ref]["property"].get("owner_email")
            prompt = owner_prompt(profiles[ref], load_voice(self.folder), load_knowledge(self.folder / OWNER_FOLDER),
                                  report, items, now, extra,
                                  load_knowledge(owner_folder(self.folder, owner)) if owner else [])
            return ref, prompt, {"emails": items}

    def farewell(self, property_ref, item_id):
        """02/10, «Encerrar contacto»: this customer's reply becomes a cordial goodbye (the closing's prompt), which the
        owner reviews and sends; once sent, no more rounds or reminders — without the grey list."""
        with locked(self.folder, wait=SHORT_WAIT):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            item = next((entry for entry in data["emails"] if entry["id"] == item_id), None)
            if item is None or not item.get("recipient") or item.get("kind") not in ("lead", "follow_up"):
                raise ValueError("Só se encerra o contacto a partir de um email do cliente, com destinatário.")
            item["farewell"] = True
            self.save(data, ref)
            self.log("farewell_marked", reference=ref, message_id=item_id)
        return ref

    def mark_fields(self, ref, item, data):
        """02/10: what this email's hidden mark says (mark.py): the property, our nth email to the customer, the kind, the
        visit and the visit window it names, and their place on the short list in a documents request."""
        email = recipient_email(item)
        kind = "farewell" if item.get("farewell") else item.get("kind") or "email"
        if kind == "owner":
            talk = (data.get("owner_conversations") or {}).get(email) or {}
            return {"ref": ref, "n": len(talk.get("sent_message_ids") or []) + 1, "k": "owner"}
        conversation = data.get("conversations", {}).get(email) or {}
        stage = conversation.get("stage", 0)
        aux = item.get("kind") in AUX_KINDS or bool(item.get("answered_directly"))
        number = stage if aux else max(stage + 1, 3) if item.get("kind") == "visit_proposal" else stage + 1
        visit = (item.get("visit_slot") or (item.get("visit_done") or {}).get("at")
                 or (item.get("visit_reminder") or {}).get("at") or (item.get("visit_missed") or {}).get("at"))
        window = item.get("visit_window") or {}
        return {"ref": ref, "n": number, "k": kind, "vis": str(visit).replace(" ", "T") if visit else None,
                "win": f"{window['day']}/{window['start']}-{window['end']}" if window.get("day") else None,
                "sel": (conversation.get("selection") or {}).get("status") if item.get("kind") == "docs_request" else None}

    def put_mark(self, msg, ref, item, data, key):
        """02/10: the hidden mark — our own Message-ID (the reply carries it back) and the X-ARIA header (our copy)."""
        fields = self.mark_fields(ref, item, data)
        del msg["Message-ID"]
        msg["Message-ID"] = mark.message_id(fields, key)
        msg["X-ARIA"] = mark.header(fields, key)

    def interaction_notice(self, ref, data, item):
        """02/10, the board: our conclusive 8th email went out with no visit booked (the owner steps in), or the closing."""
        if item.get("kind") not in ("lead", "follow_up") or item.get("survey_reply") or item.get("farewell"):
            return  # a farewell is the owner's own decision: nothing to tell them
        email = ((item.get("recipient") or {}).get("email") or "").casefold()
        conversation = data.get("conversations", {}).get(email) or {}
        stage = conversation.get("stage", 0)
        if stage not in (CONCLUSIVE_AT, CLOSING_FROM) or conversation.get("visit_check"):
            return
        today = date.today().isoformat()
        if any(slot["customer"] == email and slot["at"][:10] >= today for slot in load_visits(self.folder, ref)["slots"]):
            return
        name = shown_name(conversation.get("name"), "Um cliente")
        key = f"interacao-{stage}-{ref}-{hashlib.sha256(email.encode()).hexdigest()[:8]}"
        if stage == CONCLUSIVE_AT:
            self.notify(key, f"{name} ({ref}): foi a {CONCLUSIVE_AT}.ª interação sem visita marcada. Precisa da tua "
                        "intervenção — lista cinzenta, propor-lhe uma visita ou deixar seguir para o fecho.",
                        ref, "warn", "contacts")
        else:
            self.notify(key, f"{name} ({ref}): levou o email de fecho ({CLOSING_FROM}.ª interação). Deixamos de "
                        "insistir: fica fora das rondas de visitas.", ref, "ok", "contacts")

    @classmethod
    def advance(cls, data, item):
        """After a successful send: the customer's conversation moves to the next interaction.

        A reminder, a consent request or a visits-closed notice never counts as an interaction and never
        resets last_sent_at: the 2/4-day reminders keep measuring from the last real exchange.
        """
        if item.get("kind") == "owner":  # 02/10: the owner's conversation: their own, no interaction to count
            email = ((item.get("recipient") or {}).get("email") or "").casefold()
            talk = data.setdefault("owner_conversations", {}).setdefault(email, {"sent_message_ids": [], "thread_ids": []})
            talk["sent_message_ids"].append(item["reply_message_id"])
            if item.get("thread_id") and item["thread_id"] not in talk["thread_ids"]:
                talk["thread_ids"].append(item["thread_id"])
            if item.get("reply_text"):
                cls.append_history(talk, "nos", item["reply_text"], now()[:10], now())
            talk["last_sent_at"] = now()
            return
        # The stage outlives the email in the queue. Kept: address, name, our last subject, IDs, dates,
        # the last text sent (so a reminder can quote it), the visit status, and the last HISTORY_LIMIT
        # turns of the conversation (ours and the customer's), for context in the next prompt.
        created = item["recipient"]["email"].casefold() not in data["conversations"]
        conversation = data["conversations"].setdefault(
            item["recipient"]["email"].casefold(), {"stage": 0, "sent_message_ids": [], "thread_ids": []})
        message = (item.get("customer") or {}).get("message")
        if (item.get("customer") or {}).get("portal_lang"):  # 06/10: the language chosen on the portal (its flag)
            conversation.setdefault("portal_lang", item["customer"]["portal_lang"])
        if created and item.get("kind") == "lead" and message:
            # 26/09: the portal notice that started it all goes into the history too, before our first reply (until
            # then only later messages were kept, and the file and the prompts lost what the customer first said).
            cls.append_history(conversation, "cliente", message, contact_day(item), item.get("date"))
        # An email the owner already answered in Gmail spent its step then: one more email to it is an addition.
        aux = item.get("kind") in AUX_KINDS or bool(item.get("answered_directly"))
        if not aux:
            stage = conversation["stage"] + 1
            conversation["stage"] = max(stage, 3) if item.get("kind") == "visit_proposal" else stage
        if item.get("kind") == "visit_proposal":
            conversation["visit_proposed"] = True  # the qualification is over for them
        if item.get("farewell"):
            conversation["closed_at"] = now()  # 02/10: «Encerrar contacto»: no rounds or reminders from now on
        selection = conversation.get("selection") or {}
        if (item.get("kind") in ("lead", "follow_up") and selection.get("status") in SELECTION_STATES
                and not selection.get("docs_requested_at")):
            selection["docs_requested_at"] = now()  # 03/10: the short list's reply asked for the documents
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
        if item.get("kind") == "visit_reminder" and item.get("visit_reminder"):
            sent = conversation.setdefault("visit_reminders_sent", [])
            sent.append(f"{item['visit_reminder']['at']}|{item['visit_reminder']['when']}")
            del sent[:-20]

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

        Stops for a customer who answered (a pending email from them), whose reminder was dismissed, who has a
        visit booked or done, who is inactive, or once visits are closed. With a phrase in the voice, the phrase
        goes over the last text sent; without one (26/09), the assistant writes the reminder (REMINDER_RULE).
        """
        agenda = load_visits(self.folder, ref)
        if agenda.get("closed_at"):
            return 0
        booked = {slot["customer"] for slot in agenda["slots"] if slot["at"][:10] >= date.today().isoformat()}
        proposed = self.proposed_to(agenda)
        phrases = (voice.get("style", {}).get("reminders") or {})
        text = {key: (phrases.get(key) or {}).get("text") or "" for key in ("day2", "day4")}
        waiting = {((item.get("recipient") or {}).get("email") or "").casefold() for item in data["emails"]}
        already = {(((item.get("recipient") or {}).get("email") or "").casefold(), item.get("reminder"))
                  for item in data["emails"] if item.get("kind") == "reminder"}
        created = 0
        for email, conversation in data.get("conversations", {}).items():
            if (email in waiting or conversation.get("reminders_stopped") or conversation.get("ignored") or conversation.get("closed_at")
                    or not conversation.get("last_sent_at") or email in booked or conversation.get("visit_check")
                    or conversation.get("inactive") or was_proposed(conversation, email, proposed)
                    or conversation.get("stage", 0) >= 3):
                # Only in the qualification (26/09): after a visit proposal the round, the agenda and the visit
                # reminders take over; a «did you get our email?» about a day already gone would be wrong.
                continue
            sent = set(conversation.get("reminders_sent") or [])
            hours = (datetime.now(timezone.utc)
                    - datetime.fromisoformat(conversation["last_sent_at"])).total_seconds() / 3600
            # A ceiling (26/09): someone silent for more than REMINDER_MAX_HOURS gets no reminder any more, so a
            # backlog of old conversations never turns into a pile of reminders on one read.
            if hours >= REMINDER_MAX_HOURS:
                continue
            if "2d" not in sent and hours >= REMINDER_HOURS["2d"]:
                threshold = "2d"
            elif "2d" in sent and "4d" not in sent and hours >= REMINDER_HOURS["4d"]:
                threshold = "4d"
            else:
                continue
            if (email, threshold) in already:
                continue
            phrase = text["day2"] if threshold == "2d" else text["day4"]
            key = f"lembrete-{threshold}-{hashlib.sha256(email.encode()).hexdigest()[:8]}"
            if key in set(data.get("dismissed_message_ids") or []):
                continue
            if phrase:
                body = f"{phrase}\n\n{conversation['last_text']}" if conversation.get("last_text") else phrase
                data["emails"].append(self.aux_item(key, "reminder", email, conversation, body, reminder=threshold))
            else:  # no fixed phrase: the assistant writes it, with the conversation in front of it
                data["emails"].append(self.aux_item(key, "reminder", email, conversation, "", reminder=threshold,
                                                    reply_status="pending",
                                                    history=list(conversation.get("history") or [])))
            created += 1
        return created

    def set_recipient(self, property_ref, key, email):
        """«Mudar destinatário»: on a portal notice without a valid Reply-To, the owner sets who the reply goes to.
        The portal's address and the account itself are refused, as for a Reply-To."""
        email = str(email or "").strip()
        if not EMAIL.fullmatch(email):
            raise ValueError("Indica um email válido.")
        with locked(self.folder):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref)
            account = self.config()["account"]
            never = {a.casefold() for a in profiles[ref].get("reply", {}).get("never_reply_to", [])} | {account.casefold()}
            if email.casefold() in never:
                raise ValueError("Esse endereço é do portal ou teu: indica o email do cliente.")
            data = self.load(ref)
            item = next((entry for entry in data["emails"] if entry["id"] == key), None)
            if (not item or item.get("kind") != "lead" or (item.get("reply_to") and not item.get("blocked"))
                    or item.get("reply_status") not in (None, "pending", "draft")):
                raise ValueError("Este email não permite mudar o destinatário.")
            name = (item.get("customer") or {}).get("name") or ""
            item["recipient"] = {"name": name, "email": email}
            item["customer"] = {**(item.get("customer") or {}), "email": email}
            item["blocked"] = None
            item["warnings"] = [w for w in item.get("warnings") or [] if not w.startswith("Sem Reply-To")]
            item["warnings"].append(f"Destinatário indicado à mão: {email}.")
            data.pop("send_preview", None)
            add_contacts(self.folder, [{"email": email.casefold(), "nome": name, "telefone": (item["customer"].get("phone") or ""),
                                        "primeiro_contacto": contact_day(item), "imovel": ref, "fonte": CONTACT_SOURCE}])
            self.save(data, ref)
            self.log("recipient_set", reference=ref)
            return {"property_ref": ref}

    @staticmethod
    def drop_empty_additions(data):
        """30/09: an «acrescento» (Escrever mais) with next to no text leaves the queue once the same customer writes
        again: their new email is the reply to write now (one left with «pdf» in it sat beside it as a second card)."""
        writing = {recipient_email(item) for item in data["emails"]
                   if item.get("kind") in ("lead", "follow_up") and not item.get("answered_directly")}
        empty = [item for item in data["emails"] if item.get("kind") == "addition" and recipient_email(item) in writing
                 and len(str(item.get("reply_text") or "").strip()) < ADDITION_MIN_TEXT
                 and item.get("reply_status") in (None, "pending", "draft")]
        for item in empty:
            data["emails"].remove(item)
            data["dismissed_message_ids"].append(item["id"])
        return len(empty)

    @staticmethod
    def repair_surveys(data):
        """Survey answers kept before 26/09 without any mark (written as words, or wrapped over two lines): read again
        from the customer's own reply in the history, with the reader of today. 27/09: and a survey answer still in the
        queue from before 26/09, read without the mark that gives it its prompt (it went as a plain «8.ª interação»,
        for which there is none): marked now, with today's notice."""
        fixed = 0
        for item in data.get("emails", []):
            if item.get("survey_reply") or item.get("kind") != "follow_up" or item.get("reply_status") not in (None, "pending", "draft"):
                continue
            conversation = data.get("conversations", {}).get(recipient_email(item)) or {}
            survey = ((conversation.get("visit_check") or {}).get("thanks_sent_at")
                      and parse_survey((item.get("customer") or {}).get("message") or item.get("body_text")))
            if survey:
                item["survey_reply"] = {"alerts": survey_alerts(survey)}
                item["warnings"] = [warning for warning in item.get("warnings") or []
                                    if not warning.startswith("Resposta ao inquérito pós-visita registada")] + [SURVEY_NOTICE]
                fixed += 1
        for conversation in data.get("conversations", {}).values():
            survey = conversation.get("visit_survey")
            if not survey or any(survey.get(part) for part in ("imovel", "consultor", "marcacao")):
                continue
            for turn in reversed(conversation.get("history") or []):
                again = parse_survey(turn["text"]) if turn.get("who") == "cliente" else None
                if again and any(again.get(part) for part in ("imovel", "consultor", "marcacao")):
                    conversation["visit_survey"] = {**again, "at": survey.get("at")}
                    fixed += 1
                    break
        return fixed

    def repair_missing_reply_to(self, ref, data, profile, account):
        """Portal notices already in the queue, blocked only for lacking Reply-To before 26/09 (or, 27/09, for a Reply-To
        that is the portal's own address): prepared again, so the email in their body becomes the recipient when there
        is one. Returns their contacts."""
        notices = {profile.get("reply", {}).get("missing_reply_to_notice") or "Sem Reply-To: confirma o destinatário.",
                   profile.get("reply", {}).get("invalid_reply_to_notice") or "Reply-To inválido: confirma o destinatário."}
        found = []
        for item in data["emails"]:
            if (item.get("kind") != "lead" or item.get("recipient") or item.get("blocked") not in notices
                    or item.get("reply_status") not in (None, "pending", "draft")):
                continue
            fixed = prepare(item, "lead", None, profile, account)
            if fixed["recipient"]:
                item.update(fixed)
                found.append({"email": fixed["recipient"]["email"].casefold(), "nome": fixed["customer"].get("name") or "",
                              "telefone": fixed["customer"].get("phone") or "", "primeiro_contacto": contact_day(item),
                              "imovel": ref, "fonte": CONTACT_SOURCE})
        return found

    def mark_inactive(self, ref, data, moment=None):
        """Silence, in two steps (06/10, the owner's rule). Counting our emails since the customer's last message:
        the 3rd one 48 hours unanswered makes them «ausente» (absent: only marked — still in the rounds and the
        reminders); the 4th one two working days unanswered makes them inactive: no rounds, reminders or active card.
        Nothing is sent to them, and nothing is deleted; their next email brings them back while the property is ATIVO.
        A message of theirs waiting in the queue stops the count; an email of ours waiting there (a proposal, a
        reminder) does not. Returns how many changed."""
        moment = moment or datetime.now(timezone.utc)
        waiting = {recipient_email(item) for item in data["emails"] if item.get("kind") not in PROGRAM_KINDS}
        count = 0
        for email, conversation in data.get("conversations", {}).items():
            if conversation.get("inactive") or conversation.get("ignored") or email in waiting:
                continue
            ours = []  # our emails since their last message, the oldest first
            for turn in reversed(conversation.get("history") or []):
                if turn.get("who") != "nos":
                    break
                ours.insert(0, turn)
            sent = lambda number: aware(ours[number - 1].get("ts") or ours[number - 1].get("at") or "") \
                if len(ours) >= number else None
            fourth, third = sent(INACTIVE_AFTER_EMAILS), sent(ABSENT_AFTER_EMAILS)
            reason = f"{len(ours)} emails nossos sem resposta"
            if fourth and moment >= after_workdays(fourth, INACTIVE_AFTER_WORKDAYS):
                conversation.pop("absent", None)
                conversation["inactive"] = {"at": moment.isoformat(), "reason": reason}
                count += 1
            elif third and not conversation.get("absent") and moment - third >= timedelta(hours=ABSENT_AFTER_HOURS):
                conversation["absent"] = {"at": moment.isoformat(), "reason": reason}
                count += 1
        return count

    def schedule_visit_reminders(self, ref, data, moment=None):
        """Visit reminders (26/09): one the day before the visit and one on the day, drafted at the first read of
        each of those days. The assistant writes them, in the customer's language; the owner reviews and sends.

        None for a visit already checked, a customer on a list or who asked for another date, one already sent, or
        one the owner dismissed. On the day, the day before's still unsent is replaced by the day's.
        """
        moment = moment or datetime.now()  # the agenda's times are local
        today, stamp = moment.date().isoformat(), moment.strftime("%Y-%m-%d %H:%M")
        tomorrow = (moment.date() + timedelta(days=1)).isoformat()
        dismissed = set(data.get("dismissed_message_ids") or [])
        created = 0
        for slot in load_visits(self.folder, ref)["slots"]:
            day = slot["at"][:10]
            when = "vespera" if day == tomorrow else "dia" if day == today and slot["at"] > stamp else None
            conversation = data.get("conversations", {}).get(slot["customer"])
            if (not when or not conversation or conversation.get("ignored") or slot.get("check")
                    or conversation.get("visit") in ("nao_quer", "outra_data")
                    or f"{slot['at']}|{when}" in (conversation.get("visit_reminders_sent") or [])):
                continue
            digest = hashlib.sha256(f"{slot['customer']}|{slot['at']}".encode()).hexdigest()[:8]
            key = f"lembrete-visita-{when}-{digest}"
            if key in dismissed or any(item["id"] == key for item in data["emails"]):
                continue
            if when == "dia":
                data["emails"] = [item for item in data["emails"] if item["id"] != f"lembrete-visita-vespera-{digest}"]
            data["emails"].append(self.aux_item(key, "visit_reminder", slot["customer"], conversation, "",
                                                reply_status="pending", visit_reminder={"at": slot["at"], "when": when}))
            created += 1
        return created

    def digest_recipient(self):
        """The address «Enviar» sends an owner's report to, from voice.json; leniently, not the full voice."""
        style = load_json(self.folder / "voice.json", {}).get("style") or {}
        return (style.get("digest_recipient") or {}).get("text") or ""

    @staticmethod
    def replied_after_us(conversation):
        """The customer wrote again after our first email to them («responderam», in the owner's report)."""
        history = conversation.get("history") or []
        first = next((index for index, turn in enumerate(history) if turn.get("who") == "nos"), None)
        return first is not None and any(turn.get("who") == "cliente" for turn in history[first + 1:])

    def property_view(self, ref, profile, data, voice, added=None):
        """A property as the page shows it: its queue (view) and where each of its customers stands (pipeline)."""
        view = {**self.view(ref, profile, data, voice, added, self.open_visits(ref, voice)),
                "pipeline": self.pipeline(ref, data, voice)}
        # 03/10: each customer's context (the owner's notes, our WhatsApp and SMS, their calls) and the counts, on the card
        calls = self.calls_by_customer(ref) if ref else {}
        for email in view["emails"]:
            address = recipient_email(email)
            if not address or email.get("owner"):
                continue
            # 06/10: the language the customer chose on the portal (its flag), until they write in another one
            portal_lang = ((data.get("conversations") or {}).get(address) or {}).get("portal_lang") \
                or (email.get("customer") or {}).get("portal_lang")
            if portal_lang:
                email["portal_lang"] = portal_lang
            # 06/10: silent customers, marked on their cards too
            talk = (data.get("conversations") or {}).get(address) or {}
            if talk.get("inactive") or talk.get("absent"):
                email["silence"] = {"state": "inativo" if talk.get("inactive") else "ausente",
                                    "reason": (talk.get("inactive") or talk.get("absent") or {}).get("reason") or ""}
            context = self.context_of(data, address, calls.get(address, []))
            email["context"] = context
            email["contact_counts"] = {"calls": sum(1 for entry in context if entry["source"] == "call"),
                                       "answered": sum(1 for entry in context if entry.get("answered")),
                                       "whatsapp": sum(1 for entry in context if entry["source"] == "whatsapp"),
                                       "sms": sum(1 for entry in context if entry["source"] == "sms")}
        return view

    # ===== The customer's context (03/10): what happened outside the emails and what only the agency knows — the
    # owner's notes, our WhatsApp and SMS (opened from the page), their calls (the portal's notices, by the phone). It
    # goes in the prompt of that customer's emails only; each entry goes with one click (a call is hidden from it).

    CONTEXT_SOURCES = ("manual", "whatsapp", "sms")

    def calls_by_customer(self, ref):
        """email → this property's calls tied to that customer by the phone (Contactos)."""
        index = {}
        for (email, row_ref), row in load_contacts(self.folder).items():
            if row_ref == ref and row.get("telefone"):
                index.setdefault(phone_key(row["telefone"]), set()).add(email)
        found = {}
        for call in load_calls(self.folder)["calls"]:
            if call.get("property_ref") not in (ref, None):
                continue
            for email in index.get(phone_key(call.get("phone")), ()):
                found.setdefault(email, []).append(call)
        return found

    @staticmethod
    def context_of(data, email, calls):
        """The customer's context as the page and the prompt see it, the oldest first; local times «AAAA-MM-DD HH:MM»."""
        hidden = set((data.get("context_hidden") or {}).get(email) or [])
        entries = [dict(entry) for entry in (data.get("customer_context") or {}).get(email) or []]
        for call in calls:
            if call["id"] in hidden:
                continue
            text = ("Ligou-nos — atendida" + (f" ({call['seconds']} s)" if call.get("seconds") else "")
                    if call.get("answered") else "Ligou-nos — não atendida")
            entries.append({"id": call["id"], "at": str(call.get("at") or "")[:16], "source": "call", "text": text,
                            "answered": bool(call.get("answered"))})
        return sorted(entries, key=lambda entry: str(entry.get("at") or ""))

    def add_context(self, property_ref, email, text, source="manual"):
        """One entry of a customer's context: a note of the owner's, or a WhatsApp or SMS we opened from the page."""
        email = str(email or "").strip().casefold()
        text = " ".join(str(text or "").split())
        if source not in self.CONTEXT_SOURCES:
            raise ValueError("Origem desconhecida.")
        if source == "manual" and not 1 <= len(text) <= 500:
            raise ValueError("Escreve o contexto numa ou duas frases (até 500 caracteres).")
        if source != "manual":
            text = f"Abrimos o {'WhatsApp' if source == 'whatsapp' else 'SMS'} para lhe escrever"
        with locked(self.folder, wait=SHORT_WAIT):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            entries = data.setdefault("customer_context", {}).setdefault(email, [])
            entries.append({"id": secrets.token_hex(5), "at": datetime.now().strftime("%Y-%m-%d %H:%M"), "source": source,
                            "text": text})
            del entries[:-50]
            self.save(data, ref)
        self.log("context_added", reference=ref, source=source)

    def delete_context(self, property_ref, email, entry_id=None):
        """Takes an entry out of a customer's context (a call is hidden from it); without entry_id, all of it."""
        email = str(email or "").strip().casefold()
        with locked(self.folder, wait=SHORT_WAIT):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            entries = (data.get("customer_context") or {}).get(email) or []
            calls = [call["id"] for call in self.calls_by_customer(ref).get(email, [])]
            hidden = data.setdefault("context_hidden", {}).setdefault(email, [])
            if entry_id is None:
                data.setdefault("customer_context", {})[email] = []
                hidden.extend(call for call in calls if call not in hidden)
            elif any(entry["id"] == entry_id for entry in entries):
                data["customer_context"][email] = [entry for entry in entries if entry["id"] != entry_id]
            elif entry_id in calls and entry_id not in hidden:
                hidden.append(entry_id)
            self.save(data, ref)
        self.log("context_deleted", reference=ref)

    def pipeline(self, ref, data, voice=None, moment=None):
        """27/09: each customer of a property in one column, the furthest they got — for the table above the emails.
        contacto: not answered yet; qualificacao: answered, still gathering their file (no visit proposed yet);
        pronto: their file is complete and no visit was proposed yet (the ones for the next round); proposta: a visit
        proposed (by a round or in the conversation), no time booked yet; por_confirmar: they accepted or asked for a
        time we have not confirmed yet (29/09: by phase, not by how many emails we sent — the 1.ª to «Mais de 3»
        columns said little); marcada, visitou,
        shortlist, selecionado (04/10: the one selected, golden; a line under the table, always open) and desistiu (declined
        the visit); and under the table, sem_resposta (our last email left unanswered
        NO_REPLY_DAYS or more, whatever the step, or inactive), greylist and blacklist. waiting: a message of theirs is
        in the queue for us to answer. dots, as the owner set them: orange, that message has waited longer than
        our_turn_hours; red, they never answered us, or answered without any of what we asked; green, their file is
        complete; blue instead of green, complete for no_visit_hours and still no visit date from us."""
        moment = moment or datetime.now(timezone.utc)
        hours = alert_hours(voice)
        conversations = data.get("conversations", {})
        waiting, new = {}, {}
        for item in data["emails"]:
            email = recipient_email(item)
            if not email or item.get("kind") in PROGRAM_KINDS or item.get("blocked") or item.get("answered_directly"):
                continue
            arrived = aware(item.get("date")) or moment
            waiting[email] = min(waiting.get(email, arrived), arrived)
            if email not in conversations:
                new.setdefault(email, item)
        agenda = load_visits(self.folder, ref) if ref else {"windows": [], "slots": []}
        slots, proposed = agenda["slots"], self.proposed_to(agenda) if ref else set()
        visited = {slot["customer"] for slot in slots if (slot.get("check") or {}).get("attended") is True}
        booked = {slot["customer"] for slot in slots if (slot.get("check") or {}).get("attended") is not False}
        try:  # 04/10: a registered owner in the table gets a frame of their own
            owners = {email.casefold() for email in self.owner_index(self.profiles())}
        except Exception:
            owners = set()
        customers = []
        for email in set(conversations) | set(new):
            conversation = conversations.get(email) or {}
            history = conversation.get("history") or []
            stage = conversation.get("stage", 0)
            selection = (conversation.get("selection") or {}).get("status")
            sent = aware(conversation.get("last_sent_at"))
            silent = bool(stage and (not history or history[-1].get("who") == "nos")
                          and sent and moment - sent >= timedelta(days=NO_REPLY_DAYS))
            if conversation.get("ignored"):
                column = "blacklist" if ignore_kind(conversation) == "black" else "greylist"
            elif conversation.get("visit") == "nao_quer":
                column = "desistiu"
            elif selection == "chosen":
                column = "selecionado"  # 04/10: the one selected (documents in, a contract to prepare elsewhere)
            elif selection in SELECTION_STATES:
                column = "shortlist"
            elif email in visited:
                column = "visitou"
            elif email in booked:
                column = "marcada"
            elif email not in waiting and stage and (conversation.get("inactive") or conversation.get("absent") or silent):
                column = "sem_resposta"
            else:
                complete = ficha_summary(conversation.get("ficha") or (new.get(email) or {}).get("ficha"))["complete"]
                column = ("contacto" if not stage
                          else "por_confirmar" if conversation.get("visit_accepted") or conversation.get("visit_offered")
                          else "proposta" if was_proposed(conversation, email, proposed)
                          else "pronto" if complete else "qualificacao")
            item = new.get(email) or {}
            # 29/09: one dot in two halves, two different things — on the left what THEY gave (red: nothing yet, yellow:
            # part of the file, green: all of it, black: declined or ignored); on the right what WE have to do (late, red:
            # their message waits for us past our_turn_hours, amber: it waits, not that long yet, blue: complete for
            # no_visit_hours and still no visit date from us; ok, green: up to date; black: declined or ignored)
            ficha = conversation.get("ficha") or item.get("ficha")
            summary = ficha_summary(ficha)
            if column in ("desistiu", "greylist", "blacklist"):
                them = "black"
            elif summary["complete"]:
                them = "green"
            elif stage and (not self.replied_after_us(conversation) or not summary["known"]):
                them = "red"
            else:
                them = "yellow" if summary["known"] else None
            us = None
            if column != "blacklist" and email in waiting:
                # 29/09: overdue is red, so a dot all red is really bad (and one all green really good)
                us = "late" if moment - waiting[email] >= timedelta(hours=hours["our_turn_hours"]) else "amber"
            elif summary["complete"] and column not in ("desistiu", "greylist", "blacklist"):
                done = aware(ficha.get("complete_at") or ficha.get("at"))
                if (done and moment - done >= timedelta(hours=hours["no_visit_hours"]) and email not in booked
                        and not was_proposed(conversation, email, proposed)):
                    us = "blue"
            if us is None:
                # 29/09: up to date — we have answered, or nothing needs an answer (green on the right); one who declined
                # or is ignored, all black. An empty half is only «incógnito»: nothing known yet (a new request's left)
                us = "black" if them == "black" else "ok"
            dots = [color for color in (them, us) if color]
            last = history[-1].get("ts") or history[-1].get("at") if history else item.get("date")
            customers.append({"email": email, "column": column, "waiting": email in waiting, "selection": selection,
                              "owner": email.casefold() in owners,
                              "dots": dots, "them": them, "us": us, "reason": (conversation.get("ignored_reason") or "")
                              if column in ("greylist", "blacklist") else "",
                              "name": conversation.get("name") or (item.get("customer") or {}).get("name") or "",
                              "last_at": last or conversation.get("last_sent_at")})
        return sorted(customers, key=lambda customer: str(customer["last_at"] or ""), reverse=True)

    def owner_report(self, ref, profile, data, moment=None):
        """27/09: a property's situation as its owner reads it, not the queue's: how many customers contacted us,
        answered our first email, are still active (of those who answered, the ones who have not gone silent, declined
        the visit or asked us to stop), booked a visit and came to it; the visits still to come; and who visited, with
        what their file says about their work and household. Only this property's customers: each owner gets their own
        report."""
        moment = moment or datetime.now()  # the agenda's times are local
        stamp = moment.strftime("%Y-%m-%d %H:%M")
        conversations = data.get("conversations", {})
        new = {recipient_email(item) for item in data["emails"]
               if item.get("kind") not in PROGRAM_KINDS and not item.get("blocked")} - set(conversations) - {""}
        answered = [conversation for conversation in conversations.values() if self.replied_after_us(conversation)]
        slots = sorted(load_visits(self.folder, ref)["slots"], key=lambda slot: slot["at"])
        visited = {}
        for slot in slots:
            if (slot.get("check") or {}).get("attended") is True:
                conversation = conversations.get(slot["customer"]) or {}
                ficha = conversation.get("ficha") or {}
                visited[slot["customer"]] = {"name": conversation.get("name") or slot.get("name") or "(sem nome)",
                                             "at": slot["at"], "trabalho": ficha.get("trabalho"),
                                             "agregado": ficha.get("agregado")}
        return {"property_ref": ref, "description": profile["property"].get("description") or ref,
                "owner_email": profile["property"].get("owner_email") or "",
                "active": property_active(profile), "contacted": len(conversations) + len(new),
                "responded": len(answered),
                "still_active": sum(1 for conversation in answered if not (conversation.get("ignored")
                                    or conversation.get("inactive") or conversation.get("visit") == "nao_quer")),
                "booked": len({slot["customer"] for slot in slots}), "visited": list(visited.values()),
                "upcoming": [slot["at"] for slot in slots if slot["at"] > stamp and not slot.get("check")]}

    @staticmethod
    def owner_report_text(report, today, signature=""):
        """The report for the owner (27/09), to send from the page or to copy into an email or a WhatsApp: what is
        done so far, what is in progress, and who visited. Nothing of the queue's inner work (drafts, emails waiting)."""
        def count(number, one, many):
            return f"{number} {one if number == 1 else many}"

        def sentence(text, missing):
            return (str(text).strip().rstrip(".") + ".") if text else missing

        day = lambda at: f"{at[8:10]}/{at[5:7]}"
        visited, upcoming = report["visited"], report["upcoming"]
        lines = [f"Ponto de situação — {report['description']}", "/".join(reversed(today.split("-"))), "",
                 "Até hoje:",
                 f"- {count(report['contacted'], 'cliente contactou-nos', 'clientes contactaram-nos')};",
                 f"- {count(report['responded'], 'respondeu', 'responderam')} à nossa primeira mensagem;",
                 f"- {count(report['booked'], 'marcou', 'marcaram')} visita e "
                 f"{count(len(visited), 'já visitou', 'já visitaram')} o imóvel.",
                 "", "Em curso:",
                 f"- {count(report['still_active'], 'cliente continua', 'clientes continuam')} em conversa connosco"
                 + (";" if upcoming else ".")]
        if upcoming:
            lines.append(f"- {'Próxima visita' if len(upcoming) == 1 else 'Próximas visitas'}: "
                         + ", ".join(f"{day(at)} às {at[11:16]}" for at in upcoming) + ".")
        if visited:
            lines += ["", "Quem já visitou:"]
            for person in visited:
                lines += [f"- {person['name']} (visitou a {day(person['at'])})",
                          f"  Situação profissional: {sentence(person['trabalho'], 'ainda por saber.')}",
                          f"  Agregado familiar: {sentence(person['agregado'], 'ainda por saber.')}"]
        if signature:
            lines += ["", signature]
        return "\n".join(lines)

    def today_digest(self):
        """digest.json as today's pages, one per property (27/09); yesterday's, or the single text of before, start over."""
        digest = load_digest(self.folder) or {}
        today = date.today().isoformat()
        if digest.get("date") != today or not isinstance(digest.get("pages"), dict):
            return {"date": today, "pages": {}}
        return digest

    def owner_page(self, ref, profile, digest):
        """One property's page in the notepad: its numbers of now, and the text kept today (edited, or sent) or else
        written now from the data."""
        report = self.owner_report(ref, profile, self.load(ref))
        page = digest["pages"].get(ref) or {}
        return {**report, "reply_text": page.get("reply_text") or self.owner_report_text(report, digest["date"], REPORT_SIGNATURE),
                "reply_status": page.get("reply_status") or "draft", "reply_error": page.get("reply_error"),
                "sent_at": page.get("sent_at"), "sent_to": page.get("sent_to"), "edited": bool(page)}

    def digest_view(self):
        """The Painel's «Ponto de situação» (27/09): per property, the numbers of now and the report for its owner;
        and how today's summary of every property, for the user, went."""
        with locked(self.folder):
            profiles = load_profiles(self.folder, self.config()["account"])
            digest = self.today_digest()
            return {"date": digest["date"], "recipient": self.digest_recipient(), "all": digest.get("all"),
                    "properties": [self.owner_page(ref, profile, digest) for ref, profile in profiles.items()
                                   if not profile.get("test")]}  # 29/09: no report for the test property

    def digest_page(self, profiles, property_ref, digest, changing=True):
        """The property and its page kept today (None: not edited yet). A page that went, or may have gone, is final."""
        ref = self.pick(profiles, property_ref)
        if not ref:
            raise ValueError("O ponto de situação é de um imóvel: configura um imóvel primeiro.")
        page = digest["pages"].get(ref)
        if page and page.get("reply_status") not in (("draft", "error") if changing else ("draft", "error", "uncertain")):
            raise ValueError("O ponto de situação deste imóvel já foi enviado hoje."
                             if page.get("reply_status") == "sent" else "Envio incerto: verifica Enviados no Gmail.")
        return ref, page

    def save_digest_text(self, text, property_ref=None):
        """The owner's report as edited in the notepad: kept for the day, until «Atualizar» or the next day."""
        text = str(text or "")
        if len(text) > 20000:
            raise ValueError("Texto demasiado longo.")
        with locked(self.folder):
            digest = self.today_digest()
            ref, page = self.digest_page(self.profiles(), property_ref, digest)
            digest["pages"][ref] = {**(page or {"reply_status": "draft", "reply_error": None, "sent_at": None}),
                                    "reply_text": text, "saved_at": now()}
            save_digest(self.folder, digest)
            return digest["pages"][ref]

    def refresh_digest(self, property_ref=None):
        """«Atualizar com a situação de agora»: forgets the text edited today, so the report is written again now."""
        with locked(self.folder):
            digest = self.today_digest()
            ref, page = self.digest_page(self.profiles(), property_ref, digest)
            if page:
                digest["pages"].pop(ref)
                save_digest(self.folder, digest)
        return self.digest_view()

    def mail_report(self, digest, entry, recipient, subject, text, cc=None):
        """Sends one report and records on entry (a page, or the summary of all) how it went: «sending» is saved first,
        so a crash in the middle is never taken for «not sent»."""
        cfg = self.config()
        msg = build_digest(cfg["account"], recipient, subject, text, cc)
        password = app_password(self.folder, cfg["account"])
        entry.update(reply_status="sending", reply_error=None)
        save_digest(self.folder, digest)
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
                smtp.login(cfg["account"], password)
                refused = smtp.send_message(msg)
                if refused:
                    raise smtplib.SMTPRecipientsRefused(refused)
        except smtplib.SMTPResponseException as exc:
            entry.update(reply_status="error", reply_error=f"SMTP {exc.smtp_code}")
        except smtplib.SMTPRecipientsRefused:
            entry.update(reply_status="error", reply_error="Destinatário recusado pelo SMTP.")
        except Exception:
            entry.update(reply_status="uncertain", reply_error="Ligação interrompida; verifica Enviados no Gmail antes de repetir.")
        else:
            entry.update(reply_status="sent", sent_at=now())
        save_digest(self.folder, digest)

    def send_digest(self, confirmed, property_ref=None, to="me"):
        """One property's report, as it stands in the notepad, never without a click (27/09): to="owner" sends it to the
        property's owner (the email in Imóveis), with a copy to the address in Voz e estilo; to="me", only to that
        address, for the user to forward. Once a day per property, whichever way it went."""
        if confirmed is not True:
            raise ValueError("É necessária confirmação explícita do utilizador após rever o texto.")
        if to not in ("owner", "me"):
            raise ValueError("Destino inválido.")
        with locked(self.folder):
            profiles, digest = self.profiles(), self.today_digest()
            ref, page = self.digest_page(profiles, property_ref, digest, changing=False)
            mine = self.digest_recipient()
            owner = profiles[ref]["property"].get("owner_email") or ""
            recipient = owner if to == "owner" else mine
            if to == "owner" and not EMAIL.fullmatch(recipient):
                raise ValueError("Este imóvel não tem o email do proprietário: põe-no em Imóveis, nos dados do imóvel.")
            if to == "me" and not EMAIL.fullmatch(recipient):
                raise ValueError("Configura um destinatário válido em Voz e estilo.")
            if not page:
                report = self.owner_report(ref, profiles[ref], self.load(ref))
                page = {"reply_text": self.owner_report_text(report, digest["date"], REPORT_SIGNATURE),
                        "reply_status": "draft", "reply_error": None, "sent_at": None}
            digest["pages"][ref] = page
            page["sent_to"] = to
            description = profiles[ref]["property"].get("description") or ref
            subject = f"Ponto de situação — {description} — {'/'.join(reversed(digest['date'].split('-')))}"
            cc = mine if to == "owner" and EMAIL.fullmatch(mine) else None
            self.mail_report(digest, page, recipient, subject, page["reply_text"], cc)
            self.log("digest_send", status=page["reply_status"], reference=ref, to=to)
            return {"status": page["reply_status"], "property_ref": ref}

    def send_digest_all(self, confirmed):
        """The summary of every property, one after the other as they stand in the notepad, to the address in Voz e
        estilo (27/09, the option kept from before): the user decides what to do with each. It leaves the pages as
        they are, so each can still go to its owner; once a day."""
        if confirmed is not True:
            raise ValueError("É necessária confirmação explícita do utilizador após rever o texto.")
        with locked(self.folder):
            recipient = self.digest_recipient()
            if not EMAIL.fullmatch(recipient):
                raise ValueError("Configura um destinatário válido em Voz e estilo.")
            profiles, digest = self.profiles(), self.today_digest()
            profiles = {ref: profile for ref, profile in profiles.items() if not profile.get("test")}  # 29/09
            if not profiles:
                raise ValueError("O ponto de situação é de um imóvel: configura um imóvel primeiro.")
            entry = digest.get("all") or {}
            if entry.get("reply_status") in ("sent", "sending"):
                raise ValueError("O resumo de todos os imóveis já foi enviado hoje."
                                 if entry["reply_status"] == "sent" else "O resumo de todos os imóveis está a ser enviado.")
            parts = []
            for ref, profile in profiles.items():
                text = self.owner_page(ref, profile, digest)["reply_text"].rstrip()
                parts.append(text[:-len(REPORT_SIGNATURE)].rstrip() if text.endswith(REPORT_SIGNATURE) else text)
            day = "/".join(reversed(digest["date"].split("-")))
            digest["all"] = entry
            self.mail_report(digest, entry, recipient, f"Ponto de situação — todos os imóveis — {day}",
                             ("\n\n" + "—" * 24 + "\n\n").join(parts) + "\n\n" + REPORT_SIGNATURE)
            self.log("digest_send_all", status=entry["reply_status"], properties=len(parts))
            return {"status": entry["reply_status"]}

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
            subject = item.get("new_subject") or (subject_of(item.get("kind"), template, profiles[ref]) if ref else None)
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
            try:
                key = tag_key(self.folder, data["account"])
            except Exception:
                key = None  # 02/10: without the mark's key the email still goes, only without its mark
            messages = []
            for item in entries:
                msg, recipient = compose(item)
                if key and ref:
                    self.put_mark(msg, ref, item, data, key)
                messages.append((item, msg, recipient))
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
                            self.interaction_notice(ref, data, item)
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
                    self.interaction_notice(ref, data, item)
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
                "booked_at": {slot["customer"]: slot["at"] for slot in sorted(agenda["slots"], key=lambda slot: slot["at"])
                              if slot["at"][:10] >= today},
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
            if conversation.get("ignored") or conversation.get("inactive"):
                # On the ignore list, or inactive after two unanswered emails: never a visit candidate, never
                # counted as active anywhere else that reuses this list (round proposals, the analysis prompt,
                # "Clientes ativos", the files in Contactos).
                continue
            if email in booked:
                state, reason = "booked", "já tem visita marcada"
            elif email in waiting:
                state, reason = "pending", "tem um email por responder"
            elif conversation.get("closed_at"):
                state, reason = "closed", "contacto encerrado (despedida enviada)"  # 02/10: «Encerrar contacto»
            elif conversation.get("stage", 0) >= CLOSING_FROM and not conversation.get("visit_check"):
                # 02/10: the closing went out (our CLOSING_FROM-th email): no more rounds — we stopped insisting.
                # The latest word, so before «another date» or «does not want to visit».
                state, reason = "closed", "conversa fechada (já levou o email de fecho)"
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
            data = self.load(ref)
            # 02/10: who is not in the list at all, for the round card's line (5 of 20 was a surprise): the ignored,
            # the inactive and the new requests still unanswered (no conversation until our first reply goes out)
            # Of those «por responder», the ones whose only email waiting is a visit proposal of ours (a round
            # prepared and not sent yet) are told apart: they are not waiting for an answer to what they wrote.
            conversations = data.get("conversations", {})
            address = lambda item: ((item.get("recipient") or {}).get("email") or "").casefold()
            waiting = {address(item) for item in data["emails"]} - {""}
            proposals = {address(item) for item in data["emails"] if item.get("kind") == "visit_proposal"}
            others = {address(item) for item in data["emails"] if item.get("kind") != "visit_proposal"}
            customers = self.candidates(ref, data)
            # 05/10: and who they are, for the line's names when it is opened
            named = lambda email: (conversations.get(email) or {}).get("name") or next(
                ((item.get("customer") or {}).get("name") for item in data["emails"]
                 if address(item) == email and (item.get("customer") or {}).get("name")), "") or email
            names = {"ignored": [named(e) for e, c in conversations.items() if c.get("ignored")],
                     "inactive": [named(e) for e, c in conversations.items() if c.get("inactive") and not c.get("ignored")],
                     "new": [named(e) for e in sorted(waiting - set(conversations))],
                     "proposal": [named(c["email"]) for c in customers
                                  if c["state"] == "pending" and c["email"] in proposals - others]}
            left_out = {key: len(value) for key, value in names.items()}
            return {"property_ref": ref, "customers": customers, "left_out": left_out, "left_out_names": names}

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
            data = self.load(ref)
            # 06/10: a window's proposals still in the queue, not sent
            unsent_of = lambda w: {(recipient_email(item) or "").casefold() for item in data["emails"]
                                   if (item.get("visit_window") or {}).get("id") == w["id"]}
            went_out = lambda w: any(person["email"].casefold() not in unsent_of(w) for person in w["recipients"])
            created = lambda w: w.get("created_at") or ""
            window = next((w for w in windows if w["id"] == window_id), None) if window_id else None
            newest = max(windows, key=created)
            if window is None:
                # 06/10: the last round that went out; a newer one prepared and not sent is said apart (it showed alone,
                # everyone «por enviar», as if the round sent the day before had gone nowhere)
                window = max([w for w in windows if went_out(w)] or windows, key=created)
            waiting_round = newest if newest is not window and not went_out(newest) else None
            states = {c["email"]: c for c in self.candidates(ref, data)}
            booked_at = {slot["customer"]: slot["at"] for slot in agenda["slots"]}
            # this round's proposal still in the queue: «por enviar», not «por responder» (an email of theirs waiting)
            unsent = unsent_of(window)
            theirs = {(recipient_email(item) or "").casefold() for item in data["emails"] if item.get("kind") not in PROGRAM_KINDS}
            recipients = []
            for person in window["recipients"]:
                info = states.get(person["email"], {})
                state = info.get("state", "ok")
                if state == "pending" and person["email"].casefold() in unsent:
                    state = "unsent"
                elif state == "pending" and person["email"].casefold() not in theirs:
                    state = "ok"  # only an email of ours waits for them (another round's): this one went, no answer yet
                recipients.append({"email": person["email"], "name": person.get("name") or info.get("name") or "",
                                   "state": state, "reason": info.get("reason", ""),
                                   "visit_at": booked_at.get(person["email"]) if state == "booked" else None})
            return {"property_ref": ref, "window": {key: window[key] for key in ("day", "start", "end", "created_at")},
                    "recipients": recipients,
                    "unsent_round": {key: waiting_round[key] for key in ("day", "start", "end")} if waiting_round else None}

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
        own = (load_panel(self.folder, ref) if ref else {}).get("tank")
        tank = own or load_json(self.folder / "api_fuel.json", None)
        if not own and ref and self.is_test(ref):
            # 02/10: the test property is capped too, at 3 €, until it is filled with another amount; counted, like the
            # others, from the old shared tank's fill (with none, from the first call)
            tank = {"capacity_eur": FUEL_TEST_EUR, "filled_at": (tank or {}).get("filled_at") or ""}
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
        default = FUEL_TEST_EUR if property_ref and self.is_test(property_ref) else FUEL_DEFAULT_EUR
        capacity = number_in(default if capacity_eur in (None, "") else capacity_eur, (0.5, 1000),
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

    def is_test(self, ref):
        """The test property (profile "test", 29/09)."""
        return bool(load_json(self.folder / "properties" / ref / "profile.json", {}).get("test"))

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
                             "(Imóveis) para voltar a usar a API." + ("" if self.ai_mode() == "api" else
                                                                      " O copiar/colar com o ChatGPT continua a funcionar."))

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
            model = self.model(cfg)
            summary, usage = complete(key, model, prompt_text, json_mode=False)
            self.log("openai_usage", model=model, **usage, reference=ref, cost_usd=round(estimate_cost_usd(model, **{
                k: usage[k] for k in ("prompt_tokens", "completion_tokens")}), 6))
            return {"property_ref": ref, "summary": summary, "tokens": usage, "fuel": self.api_fuel(ref)}

    def agenda_slots(self, ref, today, back_days=14):
        """The booked visits: the coming ones and those of the last back_days (None: every one, as the agenda shows
        them since 26/09 — a visit stays on record for good); each with its check and the survey answered."""
        since = "" if back_days is None else (date.fromisoformat(today) - timedelta(days=back_days)).isoformat()
        conversations = self.load(ref).get("conversations", {})
        # Every booking shows whether the customer's file is complete (live: it fills as their answers arrive).
        return sorted(({**slot, "survey": survey_of(conversations.get(slot["customer"])),
                        "ficha": ficha_summary((conversations.get(slot["customer"]) or {}).get("ficha")),
                        "selection": ((conversations.get(slot["customer"]) or {}).get("selection") or {}).get("status"),
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
                # 26/09: a no-show gets a draft (the assistant writes it, VISIT_MISSED_RULE); changed back, it goes.
                missed = [item for item in data["emails"] if item.get("kind") == "visit_missed" and recipient_email(item) == email]
                if attended is False and not missed and (conversation.get("visit_missed_for") != slot["at"]):
                    key = f"visita-falhada-{hashlib.sha256((email + slot['at']).encode()).hexdigest()[:12]}"
                    data["emails"].append(self.aux_item(key, "visit_missed", email, conversation, "", reply_status="pending",
                                                        visit_missed={"at": slot["at"]},
                                                        history=list(conversation.get("history") or [])))
                    conversation["visit_missed_for"] = slot["at"]
                elif attended is not False:
                    data["emails"] = [item for item in data["emails"] if item not in missed]
                    if missed:
                        conversation.pop("visit_missed_for", None)
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
                raise ValueError("Marca primeiro em Visitas que o cliente apareceu na visita.")
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

    def write_more(self, property_ref, email, note="", text=""):
        """«Escrever mais»: one more email to an active customer, a draft in their own conversation (Re: our
        last email). It goes through the queue like any other — prompt or by hand, preview, send — and, being
        an addition, spends no step of the conversation. 05/10: never saved empty — note, what to add (the AI writes
        the email from it), or text, the email itself (a draft)."""
        email = str(email or "").strip().casefold()
        note, text = str(note or "").strip()[:2000], str(text or "").strip()[:20000]
        if not note and not text:
            raise ValueError("Escreve o que queres acrescentar.")
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
            data["emails"].append(self.aux_item(key, "addition", email, conversation, text,
                                                reply_status="draft" if text else "pending",
                                                history=list(conversation.get("history") or []),
                                                **({"addition_note": note} if note else {})))
            self.save(data, ref)
            self.log("addition_created", reference=ref)
            return {"id": key, "property_ref": ref}

    def write_to_all(self, property_ref, audience, note):
        """04/10, «Escrever a todos»: one addition draft for each customer of the property (write_all_targets), with
        the owner's words (note) kept on it for the AI; then «Gerar respostas», review and send, like any other."""
        if audience not in WRITE_ALL_AUDIENCES:
            raise ValueError("Escolhe a quem escrever: todos os clientes ativos ou só os que não responderam.")
        note = str(note or "").strip()[:2000]
        if not note:
            raise ValueError("Escreve o que queres dizer a todos.")
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            if not ref:
                raise ValueError("Escolhe um imóvel.")
            data = self.load(ref)
            targets = write_all_targets(data)[audience]
            if not targets:
                raise ValueError("Ninguém a quem escrever com esta escolha.")
            stamp = now()
            for email in targets:
                conversation = data["conversations"][email]
                key = f"acrescento-{hashlib.sha256((email + stamp).encode()).hexdigest()[:12]}"
                data["emails"].append(self.aux_item(key, "addition", email, conversation, "", reply_status="pending",
                                                    history=list(conversation.get("history") or []), addition_note=note,
                                                    addition_scope="all"))
            self.save(data, ref)
            self.log("addition_bulk", reference=ref, audience=audience, created=len(targets))
            return {"created": len(targets), "property_ref": ref}

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

    def sync_agenda(self, property_ref=None, days_back=0):
        """«Atualizar agenda»: the API reads each active customer's conversation — their emails and ours, those
        written straight in Gmail too — and, as the owner chose (25/09), updates the agenda by itself: a day and
        time we confirmed becomes a booked visit (green); one the customer proposed or accepted, still
        unconfirmed, shows orange until then. Customers already booked, who declined or are ignored are not
        asked about, and nothing is ever booked in the past. Every property, or one; a property whose tank is
        empty or whose visits are closed is skipped and says why.
        days_back (03/10): also the visits confirmed in the last N days that have gone by — added «por registar» (came
        or not, the owner says; nothing is sent), when not on the agenda yet; for rebuilding the agenda."""
        if isinstance(days_back, bool) or not isinstance(days_back, int) or not 0 <= days_back <= 365:
            raise ValueError("Indica quantos dias para trás: de 0 a 365.")
        with locked(self.folder):
            profiles = self.profiles()
            if not profiles:
                raise ValueError("A agenda só existe com imóveis.")
            cfg = self.config()
            if not has_openai_api_key(self.folder, cfg["account"]):
                raise ValueError("Sem chave da OpenAI: guarda-a com mac/openai_key.command para usar a API.")
            key = openai_api_key(self.folder, cfg["account"])
            model = self.model(cfg)
            today = date.today().isoformat()
            since = (date.today() - timedelta(days=days_back)).isoformat() if days_back else None
            results = []
            for ref in [self.pick(profiles, property_ref)] if property_ref else list(profiles):
                agenda = load_visits(self.folder, ref)
                result = {"property_ref": ref, "confirmed": 0, "moved": 0, "accepted": 0, "offered": 0, "unbooked": 0,
                          "cleared": 0, "asked": 0, "past": 0}
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
                         (booked.get(email) or {}).get("at")) for key_id, email in ids.items()], today, since)
                    answer, usage = complete(key, model, prompt_text)
                    self.log("openai_usage", model=model, **usage, reference=ref, cost_usd=round(estimate_cost_usd(
                        model, **{k: usage[k] for k in ("prompt_tokens", "completion_tokens")}), 6))
                    for key_id, found in parse_agenda(answer, set(ids)).items():
                        email = ids[key_id]
                        conversation = conversations[email]
                        slot = booked.get(email)
                        state, at = found["state"], found["at"]
                        if since and state == "confirmada" and since <= at[:10] < today:
                            # 03/10: a visit that has gone by, rebuilt «por registar»: nothing is sent from here
                            if not any(slot["customer"] == email and slot["at"] == at for slot in agenda["slots"]):
                                agenda["slots"].append({"at": at, "customer": email, "name": conversation.get("name") or "",
                                                        "source": "api-passada", "evidence": found["evidence"], "booked_at": now()})
                                result["past"] += 1
                            continue
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
                    self.save(data, ref)
                agenda["synced_at"] = now()  # 06/10: «Última atualização» on top of Visitas
                save_visits(self.folder, ref, agenda)
                self.log("agenda_synced", reference=ref, **{k: v for k, v in result.items() if k != "property_ref"})
                results.append({**result, "fuel": self.api_fuel(ref)})
            return {"properties": results}

    # ===== «Reconstruir a partir do Gmail» (03/10): after a loss, or to start from months of replies written by hand. The
    # Gmail is read twice N days back (the first read rebuilds our conversations from Sent; the second takes the
    # customers' replies to them), then what is missing is PROPOSED, never applied: visits (from our emails' mark, or
    # read by the AI), surveys (the answers to our after-visit thanks), the short list (from the mark, or because we asked
    # for identification or the IRS — only ever asked of the short list) and the queue tidied of what was already
    # answered. The owner ticks what goes in; nothing is sent.

    SHORTLIST_ASKED = re.compile(r"\b(?:IRS|recibos? de vencimento|cart[ãa]o de cidad[ãa]o|documentos? de identifica[çc][ãa]o"
                                 r"|comprovativos? de rendimentos?)\b", re.I)

    def agenda_proposals(self, ref, days_back):
        """The visits the AI reads in the conversations (confirmed ones, past or to come, N days back), as proposals."""
        cfg = self.config()
        if not has_openai_api_key(self.folder, cfg["account"]) or self.api_fuel(ref)["empty"]:
            return []
        profiles = self.profiles()
        data = self.load(ref)
        conversations = data.get("conversations", {})
        people = [customer for customer in self.candidates(ref, data) if customer["state"] != "nao_quer"]
        ids = {f"c{number}": customer["email"] for number, customer in enumerate(people, 1)}
        if not ids:
            return []
        today = date.today().isoformat()
        since = (date.today() - timedelta(days=days_back)).isoformat()
        model = self.model(cfg)
        answer, usage = complete(openai_api_key(self.folder, cfg["account"]), model, agenda_prompt(profiles[ref], [
            (key, (conversations.get(email) or {}).get("name"), (conversations.get(email) or {}).get("history") or [], None)
            for key, email in ids.items()], today, since))
        self.log("openai_usage", model=model, **usage, reference=ref, purpose="rebuild", cost_usd=round(estimate_cost_usd(
            model, **{k: usage[k] for k in ("prompt_tokens", "completion_tokens")}), 6))
        return [{"kind": "visit", "email": ids[key], "at": found["at"], "source": "ia", "evidence": found["evidence"]}
                for key, found in parse_agenda(answer, set(ids)).items()
                if found["state"] == "confirmada" and found["at"] and found["at"][:10] >= since]

    def rebuild_scan(self, property_ref, days):
        """Reads the Gmail twice N days back and proposes what is missing (see above); kept until applied."""
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
            raise ValueError("Indica quantos dias para trás: de 1 a 365.")
        ref = self.pick(self.profiles(), property_ref)
        if not ref:
            raise ValueError("Escolhe um imóvel.")
        self.read(days)
        self.read(days)  # the customers' replies to the conversations the first read rebuilt
        try:
            from_ai = self.agenda_proposals(ref, days)
        except Exception as exc:  # the rest is still proposed
            from_ai, ai_error = [], str(exc)
        else:
            ai_error = None
        with locked(self.folder, wait=SHORT_WAIT):
            data = self.load(ref)
            conversations = data.get("conversations", {})
            slots = load_visits(self.folder, ref)["slots"]
            proposals, seen = [], set()

            def add(entry):
                key = (entry["kind"], entry["email"], entry.get("at") or entry.get("status") or "")
                if key not in seen:
                    seen.add(key)
                    name = (conversations.get(entry["email"]) or {}).get("name") or entry["email"]
                    proposals.append({"id": secrets.token_hex(4), "name": shown_name(name, entry["email"]), **entry})

            booked = {(slot["customer"], slot["at"]) for slot in slots}
            for email, talk in conversations.items():
                for found in talk.get("marks") or []:
                    if found.get("vis") and found.get("k") in ("lead", "follow_up", "visit_proposal", "farewell"):
                        at = found["vis"].replace("T", " ")[:16]
                        if (email, at) not in booked:
                            add({"kind": "visit", "email": email, "at": at, "source": "marca"})
                    if found.get("k") == "docs_request" and not talk.get("selection"):
                        add({"kind": "shortlist", "email": email, "status": found.get("sel") or "shortlist", "source": "marca",
                             "at": found.get("at")})
                    if found.get("k") == "visit_thanks" and not talk.get("visit_survey"):
                        after = [turn for turn in talk.get("history") or []
                                 if turn.get("who") == "cliente" and str(turn.get("ts") or "") > str(found.get("at") or "")]
                        survey = next((parse_survey(turn.get("text")) for turn in after if parse_survey(turn.get("text"))), None)
                        if survey:
                            add({"kind": "survey", "email": email, "survey": survey, "visit": found.get("vis"),
                                 "at": found.get("at"), "source": "marca"})
                if not talk.get("selection") and any(turn.get("who") == "nos" and self.SHORTLIST_ASKED.search(turn.get("text") or "")
                                                     for turn in talk.get("history") or []):
                    add({"kind": "shortlist", "email": email, "status": "shortlist", "source": "pedido de documentos"})
            for entry in from_ai:
                at = entry["at"][:16]
                if (entry["email"], at) not in booked and entry["email"] in conversations:
                    add({**entry, "at": at})
            # the queue tidied: what was already answered in Gmail, with nothing newer from the customer
            tidy = [item["id"] for item in data["emails"] if item.get("answered_directly") and item.get("kind") in ("lead", "follow_up")]
            if tidy:
                proposals.append({"id": "arrumar", "kind": "tidy", "email": "", "name": "", "ids": tidy, "count": len(tidy)})
            data["rebuild"] = {"at": now(), "days": days, "proposals": proposals}
            self.save(data, ref)
        self.log("rebuild_scanned", reference=ref, days=days, proposals=len(proposals))
        return {"property_ref": ref, "proposals": proposals, "ai_error": ai_error}

    def rebuild_apply(self, property_ref, ids):
        """Applies the proposals the owner ticked. Nothing is sent: past visits stay «por registar»."""
        with locked(self.folder, wait=SHORT_WAIT):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            chosen = [entry for entry in (data.get("rebuild") or {}).get("proposals") or [] if entry["id"] in set(ids or [])]
            agenda = load_visits(self.folder, ref)
            done = Counter()
            for entry in chosen:
                talk = data.get("conversations", {}).get(entry["email"]) or {}
                if entry["kind"] == "visit" and not any(slot["customer"] == entry["email"] and slot["at"] == entry["at"]
                                                        for slot in agenda["slots"]):
                    agenda["slots"].append({"at": entry["at"], "customer": entry["email"], "name": talk.get("name") or "",
                                            "source": "reconstrucao", "booked_at": now()})
                elif entry["kind"] == "shortlist" and talk and not talk.get("selection"):
                    talk["selection"] = {"status": entry.get("status") or "shortlist", "at": now(),
                                         "docs_requested_at": entry.get("at") or now()}
                elif entry["kind"] == "survey" and talk and not talk.get("visit_survey"):
                    talk["visit_survey"] = {**entry["survey"], "at": entry.get("at") or now()}
                    talk.setdefault("visit_check", {"attended": True, "checked_at": now(), "thanks_sent_at": entry.get("at")})
                elif entry["kind"] == "tidy":
                    gone = set(entry["ids"])
                    data["replied_message_ids"].extend(item["id"] for item in data["emails"] if item["id"] in gone)
                    data["emails"] = [item for item in data["emails"] if item["id"] not in gone]
                else:
                    continue
                done[entry["kind"]] += 1
            data.pop("rebuild", None)
            save_visits(self.folder, ref, agenda)
            self.save(data, ref)
        self.log("rebuild_applied", reference=ref, **done)
        return dict(done)

    def propose_visits(self, property_ref, day, start, end, emails, note="", common=False):
        """The owner's visit window, and one draft per chosen customer, in the customer's own conversation.

        The drafts are written by the assistant like any other (3rd interaction) and sent after the preview.
        Customers with an email still to answer, or a visit already booked, never get a second email.
        note: what the owner wants this round's emails to say (29/09). common: one text for everyone, reviewed and
        sent in the round's own panel, never card by card in Comunicações (a card can still be taken there)."""
        window = check_window(day, start, end)
        note = str(note or "").strip()[:2000]
        if note:
            window["note"] = note
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
                    **({"round": window["id"]} if common else {}),
                    # A snapshot of the conversation so far: the assistant proposes the visit with the
                    # same context it would have for any other reply, not as a message out of nowhere.
                    "history": list(conversation.get("history") or []),
                    "reply_text": "", "send_reply": False, "reply_status": "pending"})
                created += 1
            if note:
                existing_window["note"] = note
            save_visits(self.folder, ref, agenda)
            self.save(data, ref)
            self.log("visits_proposed", reference=ref, created=created, common=bool(common))
            return {"property_ref": ref, "created": created, "window": window, "common": bool(common)}

    @staticmethod
    def round_items(data, window_id=None):
        """A round's proposals still to send with the common text; without window_id, the latest round's."""
        items = [item for item in data["emails"] if item.get("kind") == "visit_proposal" and item.get("round")]
        if window_id is None and items:
            window_id = max(items, key=lambda item: item.get("date") or "")["round"]
        return window_id, [item for item in items if item["round"] == window_id]

    def common_round(self, property_ref=None):
        """The round being written with one text for all (29/09): its window, texts and the proposals still to send."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            if not ref:
                raise ValueError("As visitas só existem com imóveis.")
            return self.round_view(ref, self.load(ref))

    def cancel_round(self, property_ref, window_id=None, ids=None):
        """05/10, «Cancelar esta ronda»: a round prepared and not sent (one clicked by mistake, a wrong day) leaves the
        queue — its proposals still to send — and its window leaves the agenda (or only those customers, when some
        of it went out before); nothing is sent."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            window_id, items = self.round_items(data, window_id)
            items = [item for item in items if item.get("reply_status") in (None, "pending", "draft")
                     and (ids is None or item["id"] in set(ids))]  # 06/10: or only these (switched off in the panel)
            if not items:
                raise ValueError("Não há nenhuma ronda por enviar neste imóvel.")
            gone = {recipient_email(item) for item in items}
            data["emails"] = [item for item in data["emails"] if not any(item is cancelled for cancelled in items)]
            agenda = load_visits(self.folder, ref)
            for window in agenda["windows"]:
                if window.get("id") == window_id:
                    window["recipients"] = [person for person in window.get("recipients") or []
                                            if str(person.get("email") or "").casefold() not in gone]
            agenda["windows"] = [window for window in agenda["windows"]
                                 if window.get("id") != window_id or window.get("recipients")]
            save_visits(self.folder, ref, agenda)
            self.save(data, ref)
            self.log("round_cancelled", reference=ref, count=len(items))
            return {"cancelled": len(items), "property_ref": ref}

    def round_view(self, ref, data):
        window_id, items = self.round_items(data)
        if not items:
            return {"property_ref": ref, "window": None, "items": []}
        window = next((w for w in load_visits(self.folder, ref)["windows"] if w["id"] == window_id), None) \
            or items[0]["visit_window"]
        common = window.get("common") or {}
        return {"property_ref": ref, "window_id": window_id, "revision": data["revision"],
                "window": {key: window.get(key) for key in ("day", "start", "end", "note")},
                "texts": common.get("texts") or {}, "summaries": common.get("summaries") or {},
                "items": [{"id": item["id"], "name": (item.get("recipient") or {}).get("name") or "",
                           "email": (item.get("recipient") or {}).get("email") or "",
                           **((common.get("clients") or {}).get(item["id"]) or {}),
                           "reply_status": item.get("reply_status"), "reply_error": item.get("reply_error"),
                           "has_draft": bool(str(item.get("reply_text") or "").strip())} for item in items]}

    def save_round(self, property_ref, window_id, common):
        """The round's common texts (from the assistant or edited in the page) become every proposal's draft."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            window_id, items = self.round_items(data, window_id)
            if not items:
                raise ValueError("Esta ronda já não tem propostas por enviar.")
            if any(item.get("reply_status") in ("sending", "uncertain") for item in items):
                raise ValueError("Verifica primeiro no Gmail o envio com resultado incerto.")
            common = clean_round(common, [item["id"] for item in items])
            for item in items:
                item.update(reply_text=round_text(common, item["id"], self.voice_signature()), send_reply=False,
                            reply_status="draft")
            data.pop("send_preview", None)
            agenda = load_visits(self.folder, ref)
            window = next((w for w in agenda["windows"] if w["id"] == window_id), None)
            if window is not None:
                window["common"] = common
                save_visits(self.folder, ref, agenda)
            self.save(data, ref)
            self.log("round_texts_saved", reference=ref, count=len(items))
            return self.round_view(ref, data)

    def individual_round_item(self, property_ref, key):
        """One proposal of a common round goes to Comunicações, to be written and sent on its own (its draft kept)."""
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            item = next((item for item in data["emails"] if item["id"] == key and item.get("round")), None)
            if item is None:
                raise ValueError("Esta proposta já não está na ronda.")
            item.pop("round")
            self.save(data, ref)
            return self.round_view(ref, data)

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
            conversations = {(email, ref): conversation for ref in profiles
                             for email, conversation in self.load(ref).get("conversations", {}).items()}
            rows = sorted(({**row, "interactions": (conversations.get((row["email"], row["imovel"])) or {}).get("stage", 0),
                            "inactive": bool((conversations.get((row["email"], row["imovel"])) or {}).get("inactive")),
                            "absent": bool((conversations.get((row["email"], row["imovel"])) or {}).get("absent"))}
                           for row in load_contacts(self.folder).values()),
                          key=lambda row: (row["imovel"], (row["nome"] or row["email"]).casefold()))
            return {"contacts": rows, "properties": list(profiles), "rgpd_states": RGPD_STATES,
                    "inactive": [ref for ref, profile in profiles.items() if not property_active(profile)],
                    "fichas": [ficha for ref in profiles for ficha in self.fichas(ref, self.load(ref))],
                    "selection": [item for ref in profiles for item in self.selection(ref, self.load(ref))],
                    "documents": {key: label for key, (label, _) in DOCUMENTS.items()},
                    "expired": self.expired_contacts(),
                    "ficha_fields": FICHA_FIELDS}

    def selection(self, ref, data):
        """The short list of one property, for the top of Contactos: each candidate's file, the visit (who came and
        the notes), the survey and the documents' checklist. The chosen one first, then the reserve."""
        slots = {slot["customer"]: slot for slot in load_visits(self.folder, ref)["slots"]}
        order = {"chosen": 0, "suplente": 1, "shortlist": 2}
        board = []
        for email, conversation in data.get("conversations", {}).items():
            selection = conversation.get("selection") or {}
            if selection.get("status") not in SELECTION_STATES or conversation.get("ignored"):
                continue
            check = conversation.get("visit_check") or (slots.get(email) or {}).get("check") or {}
            board.append({"property_ref": ref, "email": email, "name": conversation.get("name") or "",
                          "status": selection["status"], "label": SELECTION_STATES[selection["status"]],
                          "ficha": {key: (conversation.get("ficha") or {}).get(key) for key in FICHA_FIELDS},
                          **{"ficha_" + key: value for key, value in ficha_summary(conversation.get("ficha")).items()},
                          "visit": {"at": (slots.get(email) or {}).get("at"), "attended": check.get("attended"),
                                    "private": check.get("private") or "", "public": check.get("public") or ""},
                          "survey": survey_of(conversation), "documents": documents_summary(selection),
                          "docs_requested_at": selection.get("docs_requested_at")})
        return sorted(board, key=lambda item: (order[item["status"]], item["name"].casefold()))

    def set_selection(self, property_ref, email, status):
        """Short list, chosen or reserve (None takes them off). One chosen and one reserve per property: choosing
        another puts the previous one back on the short list. The owner decides; nothing is sent from here."""
        email = str(email or "").strip().casefold()
        if status is not None and status not in SELECTION_STATES:
            raise ValueError("Estado de seleção inválido.")
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            conversation = data.get("conversations", {}).get(email)
            if not conversation:
                raise ValueError("Cliente desconhecido neste imóvel.")
            if status in ("chosen", "suplente"):
                for other in data["conversations"].values():
                    if other is not conversation and (other.get("selection") or {}).get("status") == status:
                        other["selection"]["status"] = "shortlist"
            if status is None:
                conversation.pop("selection", None)
            else:
                conversation.setdefault("selection", {}).update(status=status, at=now())
            self.save(data, ref)
            self.log("selection_set", reference=ref, status=status or "removed")
            return {"property_ref": ref}

    def set_document(self, property_ref, email, document=None, received=None, fiador=None):
        """The documents' checklist of a short-listed candidate: what arrived (ticked by the owner), and whether a
        guarantor's documents are also needed. Only ticks: the files stay in the owner's Gmail."""
        email = str(email or "").strip().casefold()
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            selection = ((data.get("conversations", {}).get(email) or {}).get("selection"))
            if not selection:
                raise ValueError("Este cliente não está na short list.")
            if fiador is not None:
                selection["fiador"] = bool(fiador)
            if document is not None:
                who, _, key = str(document).partition(":")
                if who not in ("candidato", "fiador") or key not in DOCUMENTS:
                    raise ValueError("Documento desconhecido.")
                selection.setdefault("docs", {})[document] = bool(received)
            self.save(data, ref)
            return {"property_ref": ref}

    def request_documents(self, property_ref, email):
        """«Pedir documentos»: a draft in the candidate's conversation, written by the assistant with the list;
        reviewed and sent like any other. Only for the short list."""
        email = str(email or "").strip().casefold()
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            conversation = data.get("conversations", {}).get(email)
            if not conversation or not (conversation.get("selection") or {}).get("status"):
                raise ValueError("Só se pedem documentos a quem está na short list.")
            if any(recipient_email(item) == email and item.get("kind") == "docs_request" for item in data["emails"]):
                raise ValueError("O pedido de documentos deste cliente já está na fila de Emails.")
            # 05/10: one card per customer: with one in the queue already, the request goes into it, as an instruction for
            # that reply only (the documents still missing), never a second card
            theirs = [item for item in data["emails"] if recipient_email(item) == email and item.get("kind") != "owner"
                      and item.get("reply_status") in (None, "pending", "draft")]
            if theirs:
                target = max(theirs, key=lambda item: str(item.get("date") or ""))
                missing = documents_summary(conversation["selection"])["missing"]
                target["reply_note"] = ("Pede os documentos da candidatura que ainda faltam: " + "; ".join(missing)
                                        + ", a enviar em anexo em resposta a este email; diz que servem só para avaliar "
                                          "a candidatura e são apagados no fim do processo.") if missing else (
                                       "Confirma que recebemos os documentos da candidatura e que os vamos analisar.")
                conversation["selection"]["docs_requested_at"] = now()
                self.save(data, ref)
                self.log("docs_request_attached", reference=ref)
                return {"id": target["id"], "property_ref": ref, "attached": True}
            key = f"documentos-{hashlib.sha256((email + now()).encode()).hexdigest()[:12]}"
            data["emails"].append(self.aux_item(key, "docs_request", email, conversation, "", reply_status="pending",
                                                docs_request={"fiador": bool(conversation["selection"].get("fiador"))},
                                                history=list(conversation.get("history") or [])))
            conversation["selection"]["docs_requested_at"] = now()
            self.save(data, ref)
            self.log("docs_request_created", reference=ref)
            return {"id": key, "property_ref": ref}

    def set_reply_note(self, property_ref, item_id, note):
        """05/10: the owner's instruction for one reply only (as «Pedir documentos» leaves in a card already in the
        queue); empty takes it off."""
        note = " ".join(str(note or "").split())[:2000]
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            data = self.load(ref)
            item = next((item for item in data["emails"] if item.get("id") == item_id), None)
            if item is None:
                raise ValueError("Esse email já não está na fila.")
            if note:
                item["reply_note"] = note
            else:
                item.pop("reply_note", None)
            self.save(data, ref)
            return {"property_ref": ref, "id": item_id}

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
                          "selection": (conversation.get("selection") or {}).get("status"),
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

    def expired_contacts(self, moment=None):
        """RGPD (26/09): contacts without consent («sim») whose last movement — their first contact, an email of
        theirs or of ours — is more than CONTACT_RETENTION_DAYS old. Listed for the owner; erased only on a click."""
        moment = moment or datetime.now(timezone.utc)
        limit = (moment - timedelta(days=CONTACT_RETENTION_DAYS)).isoformat()
        profiles = load_profiles(self.folder, self.config()["account"])
        conversations = {(email, ref): conversation for ref in profiles
                         for email, conversation in self.load(ref).get("conversations", {}).items()}
        expired = []
        for (email, ref), row in load_contacts(self.folder).items():
            if row.get("rgpd") == "sim" or ref not in profiles:
                continue
            conversation = conversations.get((email, ref)) or {}
            stamps = [row.get("primeiro_contacto") or "", conversation.get("last_sent_at") or ""]
            stamps += [turn.get("ts") or turn.get("at") or "" for turn in conversation.get("history") or []]
            last = max(stamps)[:10]  # by day: some stamps are days, others full times
            if last and last < limit[:10]:
                expired.append({"email": email, "imovel": ref, "name": shown_name(row.get("nome")),
                                "last": last})
        return sorted(expired, key=lambda item: item["last"])

    def purge_expired(self):
        """«Apagar»: the right to erasure applied to every expired contact, one by one, as delete_contact does."""
        with locked(self.folder):
            expired = self.expired_contacts()
        for item in expired:
            self.delete_contact(item["email"], item["imovel"])
        self.log("contacts_purged", count=len(expired))
        return {"purged": len(expired)}

    def import_profile(self, property_ref, email, text):
        """«Colar perfil do Idealista»: the portal's tenant profile (behind «Ver perfil», never in the email) pasted
        by the owner; the API turns it into the customer's file, merged with what was already known."""
        email, text = str(email or "").strip().casefold(), str(text or "").strip()
        if len(text) < 20:
            raise ValueError("Cola o perfil do cliente, copiado da página do Idealista.")
        with locked(self.folder):
            ref = self.pick(self.profiles(), property_ref)
            self.require_fuel(ref)
            if email not in self.load(ref).get("conversations", {}):
                raise ValueError("Cliente desconhecido neste imóvel.")
            cfg = self.config()
            if not has_openai_api_key(self.folder, cfg["account"]):
                raise ValueError("Sem chave da OpenAI: guarda-a com mac/openai_key.command para usar a API.")
            model = self.model(cfg)
        answer, usage = complete(openai_api_key(self.folder, cfg["account"]), model, ficha_profile_prompt(text))
        data = extract_json(answer)
        ficha = clean_ficha((data.get("ficha") if isinstance(data, dict) and "ficha" in data else data))
        if not ficha:
            raise ValueError("A resposta da API não trouxe a ficha.")
        with locked(self.folder):
            data = self.load(ref)
            conversation = data["conversations"][email]
            conversation["ficha"] = ficha_update(conversation.get("ficha"), ficha)
            self.save(data, ref)
            self.log("openai_usage", model=model, **usage, reference=ref, cost_usd=round(estimate_cost_usd(
                model, **{k: usage[k] for k in ("prompt_tokens", "completion_tokens")}), 6))
            return {"property_ref": ref, "ficha": conversation["ficha"], "fuel": self.api_fuel(ref)}

    def fill_fichas(self, property_ref=None):
        """«Preencher fichas com a IA»: the API reads each active customer's conversation and fills their file,
        merged with what was known (nothing known is lost). Every ATIVO property, or one; FICHAS_BATCH customers
        per call; a property whose tank is empty is skipped and says why."""
        with locked(self.folder):
            profiles = self.profiles()
            if not profiles:
                raise ValueError("As fichas só existem com imóveis.")
            cfg = self.config()
            if not has_openai_api_key(self.folder, cfg["account"]):
                raise ValueError("Sem chave da OpenAI: guarda-a com mac/openai_key.command para usar a API.")
            key, model = openai_api_key(self.folder, cfg["account"]), self.model(cfg)
            refs = [self.pick(profiles, property_ref)] if property_ref else [
                ref for ref, profile in profiles.items() if property_active(profile)]
            results = []
            for ref in refs:
                result = {"property_ref": ref, "asked": 0, "filled": 0}
                if self.api_fuel(ref)["empty"]:
                    results.append({**result, "skipped": "o depósito da API está vazio"})
                    continue
                data = self.load(ref)
                conversations = data.get("conversations", {})
                people = [customer["email"] for customer in self.candidates(ref, data)
                          if any(turn.get("who") == "cliente" for turn in conversations[customer["email"]].get("history") or [])]
                result["asked"] = len(people)
                for start in range(0, len(people), FICHAS_BATCH):
                    ids = {f"c{number}": email for number, email in enumerate(people[start:start + FICHAS_BATCH], 1)}
                    prompt_text = fichas_prompt(profiles[ref], [(key_id, conversations[email].get("name"),
                                                                 conversations[email].get("history") or [])
                                                                for key_id, email in ids.items()])
                    answer, usage = complete(key, model, prompt_text)
                    self.log("openai_usage", model=model, **usage, reference=ref, cost_usd=round(estimate_cost_usd(
                        model, **{k: usage[k] for k in ("prompt_tokens", "completion_tokens")}), 6))
                    for key_id, ficha in parse_fichas_batch(answer, set(ids)).items():
                        conversation = conversations[ids[key_id]]
                        conversation["ficha"] = ficha_update(conversation.get("ficha"), ficha)
                        result["filled"] += 1
                self.save(data, ref)
                self.log("fichas_filled", reference=ref, asked=result["asked"], filled=result["filled"])
                results.append(result)
            return {"fill": results}

    def profile_links(self):
        """(email, property) → the portal profile's link, from contactos.csv (27/09): for the page only."""
        return {key: row.get("perfil") or "" for key, row in load_contacts(self.folder).items() if row.get("perfil")}

    def phones(self):
        """(email, property) → phone, from contactos.csv: only for the page's WhatsApp button, never for the AI."""
        return {key: row.get("telefone") or "" for key, row in load_contacts(self.folder).items() if row.get("telefone")}

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

    # «A fazer», most urgent first: what goes out to customers today, then the queue, the agenda, the rounds, setup.
    TODO_ORDER = ("expired", "survey_alert", "visit_reminder", "uncertain", "blocked", "owner", "reply", "draft", "accepted", "check", "thanks",
                  "intervene", "ready", "brake", "setup")

    def survey_report(self, ref, data=None):
        """A property's survey report: one dial per part asked, interest, and each answer with its comment."""
        conversations = (data or self.load(ref)).get("conversations", {})
        answers = [(conversation.get("name") or "", survey_of(conversation)) for conversation in conversations.values()
                   if conversation.get("visit_survey")]
        answers.sort(key=lambda pair: pair[1].get("at") or "", reverse=True)
        return {**survey_report([survey for _, survey in answers]),
                "answers": [{"name": shown_name(name), "at": survey.get("at"), "comment": survey.get("comentario"),
                             "interest": survey.get("interesse"), "alerts": survey_alerts(survey),
                             **{part: survey.get(part) for part in ("imovel", "consultor", "marcacao")}}
                            for name, survey in answers]}

    def queue_numbers(self, ref, profile):
        """04/10: a property's queue in numbers (the Painel's «Por imóvel»), for one kept out of the totals (the test one)."""
        data = self.load(ref)
        emails = [item for item in data["emails"] if item.get("kind") != "owner"]
        status = Counter(item.get("reply_status") or "pending" for item in emails)
        waits = [waited_hours(item) for item in emails if item.get("kind") in ("lead", "follow_up") and not item.get("blocked")
                 and not item.get("answered_directly") and item.get("reply_status") in (None, "pending", "draft")]
        listing = profile.get("property") or {}
        return {"property_ref": ref, "description": listing.get("description"), "test": True,
                "advertised_rent_eur": listing.get("advertised_rent_eur"),  # 04/10: «Por imóvel» shows the rent
                "pending": len(emails), "drafts": status["draft"], "blocked": sum(1 for item in emails if item.get("blocked")),
                "attention": status["uncertain"] + status["error"] + status["sending"],
                "answered": sum(conversation.get("stage", 0) for conversation in (data.get("conversations") or {}).values()),
                "reply_hours": None, "oldest_wait_hours": max([hours for hours in waits if hours is not None], default=None),
                "client_reply_hours": client_reply_hours(data.get("conversations"),  # 06/10
                                                         datetime.now(timezone.utc) - timedelta(days=REPLY_TIME_DAYS)),
                "no_reply": no_reply_share(data.get("conversations")),
                # 04/10: enough for its panel in Imóveis (the instruments), the rest reads zero there
                "customers": len(data.get("conversations") or {}), "last_read_at": data.get("last_read_at"),
                "visits_booked": sum(1 for slot in load_visits(self.folder, ref)["slots"] if slot["at"][:10] >= date.today().isoformat()),
                "reply_hours_max": self.panel(ref)["reply_hours_max"],
                "ignored": dict(Counter(ignore_kind(c) for c in (data.get("conversations") or {}).values() if c.get("ignored")))}

    def todo(self):
        """«A fazer» (26/09), right under the dashboard's telemetry: what needs doing now, worked out from the data.
        Nothing is typed by hand, and a task goes away once it is done. Of the customers, only their names leave
        this call (as in metrics; 04/10: first name and surname, shown_name): never an address or a phone."""
        def first_names(names):
            return [shown_name(name) for name in names]

        def name_of(item):
            return (item.get("recipient") or {}).get("name") or (item.get("customer") or {}).get("name") or ""

        tasks = []

        def add(kind, tab, ref, names, text):
            if names:
                tasks.append({"kind": kind, "tab": tab, "property_ref": ref, "count": len(names),
                              "names": first_names(names)[:8], "text": text})

        with locked(self.folder):
            profiles = load_profiles(self.folder, self.config()["account"])
            style = load_json(self.folder / "voice.json", {}).get("style") or {}
            moment = datetime.now()  # the agenda's times are local
            today, stamp = moment.date().isoformat(), moment.strftime("%Y-%m-%d %H:%M")
            for ref, profile in profiles.items():
                if profile.get("test"):
                    continue  # 29/09: the Painel's «A fazer» never lists the test property
                data = self.load(ref)
                emails, conversations = data["emails"], data.get("conversations", {})
                reminders = [item for item in emails if item.get("kind") == "visit_reminder"]
                surveys = [item for item in emails if (item.get("survey_reply") or {}).get("alerts")]
                add("survey_alert", "replies", ref, [name_of(item) or (conversations.get(
                    ((item.get("recipient") or {}).get("email") or "").casefold()) or {}).get("name") for item in surveys],
                    "Inquéritos com nota má ou sem interesse: ler e responder")
                uncertain = [item for item in emails if item.get("reply_status") in ("sending", "uncertain")]
                blocked = [item for item in emails if item.get("blocked")]
                owner_mail = [item for item in emails if item.get("kind") == "owner"]  # 02/10: the Proprietários tab
                add("owner", "owners", ref, [name_of(item) for item in owner_mail if item.get("reply_status") in (None, "pending", "draft")],
                    "Mensagens do proprietário por responder")
                rest = [item for item in emails if item not in reminders and item not in uncertain and item not in blocked
                        and item not in surveys and item not in owner_mail]
                add("visit_reminder", "replies", ref, [name_of(item) for item in reminders], "Lembretes de visita por enviar")
                add("uncertain", "replies", ref, [name_of(item) for item in uncertain],
                    "Envios com resultado incerto: confirmar no Gmail")
                add("blocked", "replies", ref, [name_of(item) for item in blocked], "Emails bloqueados: tratar à mão")
                add("reply", "replies", ref, [name_of(item) for item in rest if item.get("reply_status") in (None, "pending")],
                    "Emails por responder")
                add("draft", "replies", ref, [name_of(item) for item in rest if item.get("reply_status") == "draft"],
                    "Rascunhos por rever e enviar")
                if not property_active(profile):
                    continue  # an INATIVO property keeps only what is already in its queue
                name = lambda email: (conversations.get(email) or {}).get("name") or ""
                add("accepted", "agenda", ref, [visit["name"] for visit in self.pending_visits(ref, today, "visit_accepted")],
                    "Horas aceites pelo cliente, por confirmar")
                slots = self.agenda_slots(ref, today)
                add("check", "agenda", ref, [name(slot["customer"]) for slot in slots
                                              if slot["at"] < stamp and not (slot.get("check") or {}).get("checked_at")],
                    "Visitas por registar: veio ou não veio")
                thanking = {(item.get("recipient") or {}).get("email") for item in emails if item.get("kind") == "visit_thanks"}
                add("thanks", "agenda", ref, [name(slot["customer"]) for slot in slots
                                               if (slot.get("check") or {}).get("attended") is True
                                               and not slot.get("thanks_sent_at") and slot["customer"] not in thanking],
                    "Agradecimentos pós-visita por criar")
                proposed = self.proposed_to(load_visits(self.folder, ref))
                ready, brake, intervene = [], [], []
                for customer in self.candidates(ref, data):
                    conversation = conversations[customer["email"]]
                    # 02/10: our conclusive 8th email went out with no visit booked: the owner steps in before the closing
                    if (conversation.get("stage", 0) == CONCLUSIVE_AT and customer["state"] not in ("booked", "closed")
                            and not conversation.get("visit_check")):
                        intervene.append(customer["name"])
                    if customer["state"] != "ok" or was_proposed(conversation, customer["email"], proposed):
                        continue
                    if ficha_summary(conversation.get("ficha"))["complete"]:
                        ready.append(customer["name"])
                    elif conversation.get("stage", 0) >= 4:
                        brake.append(customer["name"])
                add("intervene", "contacts", ref, intervene, f"{CONCLUSIVE_AT}.ª interação sem visita marcada: decidir "
                    "(lista cinzenta, propor visita ou deixar seguir para o fecho)")
                add("ready", "properties", ref, ready, "Ficha completa, sem proposta de visita: incluir na próxima ronda")
                add("brake", "contacts", ref, brake, "Três pedidos de informação sem ficha completa: decidir se propões visita")
            expired = self.expired_contacts(moment.astimezone(timezone.utc))
            if expired:
                tasks.append({"kind": "expired", "tab": "contacts", "property_ref": None, "count": len(expired),
                              "names": [item["name"] for item in expired][:8],
                              "text": "Contactos sem consentimento com mais de 6 meses: apagar (RGPD)"})
            # The 2- and 4-day reminders are no gap any more (26/09): without a phrase, the assistant writes them.
            gaps = [label for label, done in (
                ("visitas fechadas", (style.get("visits_closed") or {}).get("text")),
                ("pedido de consentimento", (style.get("consent_request") or {}).get("text"))) if not done]
            if gaps and profiles:
                tasks.append({"kind": "setup", "tab": "voice", "property_ref": None, "count": len(gaps), "names": [],
                              "text": "Textos por escrever em Voz e estilo: " + ", ".join(gaps)})
            tasks.sort(key=lambda task: self.TODO_ORDER.index(task["kind"]))
            return {"tasks": tasks}

    def metrics(self, days=14):
        """Numbers for the dashboard. Of the customers, only names leave this call (first name and surname, shown_name): no address or phone.

        days: the chart's period, one of CHART_PERIODS; 3 months are drawn one bar per week, not per day. "all"
        (27/09, «Desde sempre»): from the first day with data, one bar per day up to a month, per week up to half a
        year, per 30 days after that.
        """
        if days != "all" and days not in CHART_PERIODS:
            raise ValueError("Período inválido: escolhe 7, 14, 30 ou 90 dias, ou desde sempre.")
        everything = days == "all"
        if everything:
            days = 1  # set once the log is read, below
        step = CHART_PERIODS.get(days, 1)
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
            # 29/09: the test property never counts in the Painel — not its tile, requests, replies, waiting times or
            # survey —, even once its customers or itself are wiped: its references and message IDs are remembered
            # in teste/clientes.json (the API's cost still counts: that money was spent)
            lab = load_json(self.folder / "teste" / "clientes.json", {})
            test_refs = {ref for ref, profile in profiles.items() if profile.get("test")} | set(lab.get("refs") or [])
            test_ids = set(lab.get("message_ids") or [])
            for ref in test_refs & set(profiles):
                data = self.load(ref)
                test_ids |= {str(key) for key in ({item["id"] for item in data["emails"]} | set(data.get("replied_message_ids") or [])
                                                   | set(data.get("dismissed_message_ids") or []))}
            refs = [ref for ref in profiles if ref not in test_refs] or [None]
            contacts = load_contacts(self.folder)
            events = load_events(self.folder, limit=100000)  # read once: the chart, the costs and every tank
            if everything:
                # The first day anything happened: a customer's email as logged at READ, or something sent.
                seen = [str(day)[:10] for event in events if event.get("event") == "read"
                        for day in (event.get("received") or {}).values()]
                seen += [str(event.get("at") or "")[:10] for event in events if event.get("event") == "send"]
                start = min((day for day in seen if DAY.fullmatch(day) and day <= today.isoformat()), default=today.isoformat())
                days = (today - date.fromisoformat(start)).days + 1
                step = 1 if days <= 31 else 7 if days <= 186 else 30
                first = date.fromisoformat(start)
            # A customer email, by message ID → the day it arrived. Three sources, most exact first:
            # the day logged at READ; the email still in the queue; a sent reply's time minus the hours the
            # customer waited (older emails that left the queue before READ logged the day).
            arrived, derived, totals, properties, last_read = {}, {}, Counter(), [], None
            # Which property each message ID belongs to: the queue, and the replied and dismissed IDs every
            # queue keeps for good. Old log events carry no property; this is how they are attributed.
            owner = {}
            # 06/10: the two reply times from the last REPLY_TIME_DAYS only (all time, the start-up's backlog — emails of
            # two weeks before, answered on 21–24/09 — made ours 163 h)
            recent = datetime.now(timezone.utc) - timedelta(days=REPLY_TIME_DAYS)
            test_waited = {}  # the test property's own, never in the totals
            today_iso = today.isoformat()
            for ref in refs:
                data = self.load(ref)
                emails = [item for item in data["emails"] if item.get("kind") != "owner"]  # 02/10: not the owner's
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
                # The one exception to "no customer data" on the dashboard (22/09): the name (04/10: shown_name), dates and
                # how many replies, for the hover of «Respostas enviadas». Never an address or a phone.
                customers = sorted(({"name": shown_name(conversation.get("name"), "(sem nome)"),
                                     "first_contact": (contacts.get((email, ref)) or {}).get("primeiro_contacto") or None,
                                     "last_reply": str(conversation.get("last_sent_at") or "")[:10] or None,
                                     "interactions": conversation.get("stage", 0)}
                                    for email, conversation in conversations.items() if conversation.get("stage")),
                                   key=lambda customer: customer["last_reply"] or "", reverse=True)
                # 27/09: what is behind the Painel's four queue numbers, for their hover (the last ten of each): the
                # name (shown_name), day, what it is and how it stands. The same exception as above: never an address or a phone.
                queue = [{"name": shown_name((item.get("customer") or {}).get("name") or (item.get("recipient") or {}).get("name"),
                                             "(sem nome)"),
                          "date": str(item.get("date") or ""), "kind": item.get("kind"),
                          "status": item.get("reply_status") or "pending", "blocked": bool(item.get("blocked"))}
                         for item in emails]
                # 04/10: the owners' emails still to answer (theirs, not the ones we wrote first) and the visits booked
                # from today on — the Painel's fourth column
                owners_pending = sum(1 for item in data["emails"] if item.get("kind") == "owner" and not item.get("outbound")
                                     and item.get("reply_status") in (None, "pending", "draft"))
                visits_booked = sum(1 for slot in slots if slot["at"][:10] >= today_iso)
                totals.update(pending=len(emails), drafts=status["draft"], blocked=blocked, answered=answered,
                              customers=len(conversations), owners_pending=owners_pending, visits_booked=visits_booked,
                              attention=status["uncertain"] + status["error"] + status["sending"])
                last_read = max([stamp for stamp in (last_read, data.get("last_read_at")) if stamp], default=None)
                listing = profiles[ref]["property"] if ref else {}
                # 04/10: how long the customer who has waited longest for us has waited (the Painel's dot by property)
                waits = [waited_hours(item) for item in emails if item.get("kind") in ("lead", "follow_up")
                         and not item.get("blocked") and not item.get("answered_directly")
                         and item.get("reply_status") in (None, "pending", "draft")]
                properties.append({"property_ref": ref, "pending": len(emails), "drafts": status["draft"],
                                   "oldest_wait_hours": max([hours for hours in waits if hours is not None], default=None),
                                   "blocked": blocked, "answered": answered, "customers": len(conversations),
                                   "attention": status["uncertain"] + status["error"] + status["sending"],
                                   "visits_booked": visits_booked, "owners_pending": owners_pending,
                                   "client_reply_hours": client_reply_hours(conversations, recent),  # 06/10
                                   "no_reply": no_reply_share(conversations),
                                   "reply_hours_max": self.panel(ref)["reply_hours_max"],
                                   "api_fuel": self.api_fuel(ref, events),
                                   "petrol": self.visit_petrol(self.panel(ref), slots),
                                   "clients": {state: clients[state] for state in
                                               ("ok", "pending", "booked", "outra_data", "nao_quer")},
                                   "ignored": {kind: ignored[kind] for kind in IGNORE_KINDS},
                                   "answered_customers": customers, "queue": queue,
                                   "last_read_at": data.get("last_read_at"), "description": listing.get("description"),
                                   "listing_url": listing.get("listing_url"),
                                   "advertised_rent_eur": listing.get("advertised_rent_eur"),
                                   "photo": bool(ref) and find_photo(self.folder, ref) is not None})
            sent, waited = Counter(), []
            openai_period, openai_all_time, unattributed = Counter(), Counter(), Counter()
            # 27/09: the wallet's own period, the last 30 days, whatever the chart shows
            openai_month, month_start = Counter(), (today - timedelta(days=29)).isoformat()
            per = {ref: {"requests": Counter(), "sent": Counter(), "waited": [], "period": Counter(),
                         "all_time": Counter()} for ref in refs}
            # 02/10: the test property's API cost, for its own tank in Depósitos (it was counted as unattributed)
            tests = {ref: {"period": Counter(), "all_time": Counter()} for ref in sorted(test_refs & set(profiles))}
            for event in events:
                if event.get("event") == "read" and isinstance(event.get("received"), dict):
                    arrived.update({key: day for key, day in event["received"].items() if str(key) not in test_ids})
                elif event.get("event") == "send" and (event.get("reference") in test_refs
                                                       or str(event.get("message_id")) in test_ids):
                    # 06/10: never in the Painel's numbers, but the test property shows its own reply time
                    hours, sent_at = event.get("waited_hours"), aware(event.get("at") or "")
                    if (event.get("status") == "sent" and event.get("reference") in test_refs and sent_at and sent_at >= recent
                            and isinstance(hours, (int, float)) and event.get("kind") not in PROGRAM_KINDS):
                        test_waited.setdefault(event["reference"], []).append(hours)
                    continue
                elif event.get("event") == "send" and event.get("status") == "sent" and event.get("kind") != "owner":
                    sent[bucket(event.get("at"))] += 1
                    ref = event.get("reference") or owner.get(str(event.get("message_id")))
                    if ref in per:
                        per[ref]["sent"][bucket(event.get("at"))] += 1
                    hours = event.get("waited_hours")
                    if isinstance(hours, (int, float)) and event.get("kind") not in PROGRAM_KINDS:
                        sent_at = aware(event.get("at") or "")
                        if sent_at and sent_at >= recent:  # 06/10: the last REPLY_TIME_DAYS
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
                    if str(event.get("at") or "")[:10] >= month_start:
                        openai_month.update(usage)
                    in_period = bucket(event.get("at")) is not None
                    if in_period:
                        openai_period.update(usage)
                    # Logged with its property since 24/09; before that there is no way to tell which one.
                    if "reference" in event and event["reference"] in per:
                        per[event["reference"]]["all_time"].update(usage)
                        if in_period:
                            per[event["reference"]]["period"].update(usage)
                    elif event.get("reference") in tests:
                        tests[event["reference"]]["all_time"].update(usage)
                        if in_period:
                            tests[event["reference"]]["period"].update(usage)
                    else:
                        unattributed.update(usage)
            merged = {key: day for key, day in {**derived, **arrived}.items() if str(key) not in test_ids}
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
            # The Painel's quality dials: every property's survey answers together (names never leave here).
            quality_all = survey_report([survey_of(conversation) for ref in refs if ref
                                         for conversation in self.load(ref).get("conversations", {}).values()])
            # 04/10: the owners with no property write to the owners' inbox: their emails to answer count too
            caixa_pending = sum(1 for item in self.load_caixa()["emails"] if not item.get("outbound")
                                and item.get("reply_status") in (None, "pending", "draft"))
            totals["owners_pending"] += caixa_pending
            return {"account": account, "last_read_at": last_read, "properties": properties, "quality": quality_all,
                    "totals": {key: totals[key] for key in ("pending", "drafts", "blocked", "attention", "answered", "customers",
                                                            "owners_pending", "visits_booked")},
                    "owners_inbox_pending": caixa_pending,
                    "period_days": days, "bucket_days": step,
                    "by_day": [{"day": day, "requests": requests.get(day, 0), "sent": sent.get(day, 0)}
                               for day in starts],
                    "reply_hours": round(sum(waited) / len(waited), 1) if waited else None,
                    "openai_usage": {"period": usage_of(openai_period), "all_time": usage_of(openai_all_time),
                                     "month": usage_of(openai_month),
                                     "unattributed": usage_of(unattributed)},
                    "api_fuel": self.api_fuel(None, events),
                    # 04/10: the test property's row for «Por imóvel» (never in the totals nor the ponto de situação)
                    "test_properties": [{**self.queue_numbers(ref, profiles[ref]), "reply_hours": round(
                        sum(test_waited[ref]) / len(test_waited[ref]), 1) if test_waited.get(ref) else None}
                        for ref in sorted(test_refs & set(profiles))],
                    # 02/10: the test property's tank, apart from the properties (it never counts in the Painel)
                    "test_tanks": [{"property_ref": ref, "api_fuel": self.api_fuel(ref, events),
                                    "openai_usage": {"period": usage_of(mine["period"]), "all_time": usage_of(mine["all_time"])}}
                                   for ref, mine in tests.items()],
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
            voice["visit_reminder"] = (style.get("visit_reminder") or {}).get("text") or VISIT_REMINDER_RULE
            voice["booked_reply"] = (style.get("booked_reply") or {}).get("text") or BOOKED_REPLY_RULE
            voice["visited_reply"] = (style.get("visited_reply") or {}).get("text") or VISITED_REPLY_RULE
            voice["docs_request"] = (style.get("docs_request") or {}).get("text") or DOCS_REQUEST_RULE
            for key, default in COMMON_PROMPTS.items():  # 30/09: the Oficina's prompts, as they stand (or the code's)
                if key not in voice and key != "application_instructions":
                    voice[key] = (style.get(key) or {}).get("text") or default
            voice["digest_recipient"] = (style.get("digest_recipient") or {}).get("text") or ""
            voice["alerts"] = alert_hours({"style": style})
            today = date.today().isoformat()
            properties = []
            events = load_events(self.folder, limit=100000)  # once, for every property's tank
            for ref, profile in load_profiles(self.folder, account).items():
                prompts = profile.get("reply", {}).get("prompts", {})
                properties.append({"sender": profile["match"]["from_address_equals"], "active": property_active(profile),
                                   "test": bool(profile.get("test")),
                                   "survey_report": self.survey_report(ref),
                                   "prompts": {name: (prompts.get(key) or {}).get(field) or ""
                                               for name, (key, field) in PROMPT_FIELDS.items()},
                                   "knowledge_files": [part["file"] for part in profile["_knowledge"]],
                                   "photo": find_photo(self.folder, ref) is not None,
                                   "api_fuel": self.api_fuel(ref, events),
                                   "visits": {"windows": [window for window in load_visits(self.folder, ref)["windows"]
                                                          if window["day"] >= today],
                                              # For the agenda only (26/09): every past window stays drawn, like the
                                              # bookings; the rounds and proposals still use only "windows".
                                              "past_windows": [window for window in load_visits(self.folder, ref)["windows"]
                                                               if window["day"] < today],
                                              "slots": self.agenda_slots(ref, today, back_days=None),
                                              "closed_at": load_visits(self.folder, ref)["closed_at"],
                                              "synced_at": load_visits(self.folder, ref).get("synced_at"),  # 06/10
                                              # Accepted by the customer, not yet confirmed (found by «Atualizar agenda»).
                                              "accepted": self.pending_visits(ref, today, "visit_accepted"),
                                              "offered": self.pending_visits(ref, today, "visit_offered")},
                                   **{key: profile["property"].get(key) for key in (
                                       "reference", "listing_id", "listing_url", "advertiser", "description",
                                       "advertised_rent_eur", "owner_email", "owner_name")}, "deal": deal_of(profile)})
            return {"account": account, "voice": voice, "properties": properties, "ai": self.ai_settings(events),
                    "auto_read": self.auto_read_settings(),  # 06/10
                    "portal_sender": portals.merged(self.config().get("portal"))["remetente_pedidos"],  # 02/10
                    "admin": self.config().get("admin") is True,  # 29/09: the Oficina shows only with "admin": true
                    "first_read_days": FIRST_READ_DAYS,
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
            # 02/10: one or more lines (a bigger signature), each tidied; the program puts it under every AI draft
            signature = "\n".join(" ".join(line.split()) for line in str(choices.get("signature") or "").splitlines()
                                  if line.strip())
            if not signature or len(signature) > 600 or signature.count("\n") > 7:
                raise ValueError("A assinatura é obrigatória (até 600 caracteres e 8 linhas).")
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
            for key, default in (("after_visit", AFTER_VISIT_RULE), ("after_visit_template", AFTER_VISIT_TEMPLATE),
                                 ("visit_reminder", VISIT_REMINDER_RULE), ("booked_reply", BOOKED_REPLY_RULE),
                                 ("visited_reply", VISITED_REPLY_RULE), ("docs_request", DOCS_REQUEST_RULE)):
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
            alerts = choices.get("alerts")
            if alerts is not None:
                if not isinstance(alerts, dict):
                    raise ValueError("Alertas inválidos.")
                values = {}
                for key in ALERT_HOURS:
                    value = alerts.get(key)
                    if isinstance(value, bool) or not isinstance(value, int) or not ALERT_HOURS_RANGE[0] <= value <= ALERT_HOURS_RANGE[1]:
                        raise ValueError("Indica as horas das bolinhas: um número de 1 a 720.")
                    values[key] = value
                style["alerts"] = {**values, "status": "configured"}
            if "digest_recipient" in choices:
                recipient = str(choices.get("digest_recipient") or "").strip()
                if recipient and not EMAIL.fullmatch(recipient):
                    raise ValueError("O destinatário do ponto de situação tem de ser um endereço de email.")
                style.setdefault("digest_recipient", {}).update(
                    text=recipient, status="configured" if recipient else "not_configured")
            save_json(path, voice)
            self.log("voice_saved")

    def save_common_prompts(self, texts):
        """30/09, Oficina: the prompts common to every property (voice.json). A text left as the code's own is kept
        empty, so it keeps following the code; an empty one goes back to it."""
        with locked(self.folder):
            path = self.folder / "voice.json"
            voice = load_json(path, None)
            if not voice:
                raise ValueError("Falta voice.json nesta pasta: corre o setup primeiro.")
            style = voice["style"]
            for key, default in COMMON_PROMPTS.items():
                if key not in texts:
                    continue
                text = str(texts.get(key) or "").strip()
                if len(text) > 5000:
                    raise ValueError("Texto demasiado longo (até 5000 caracteres).")
                if key == "application_instructions":
                    voice["application_instructions"] = text
                    continue
                same = " ".join(text.split()) == " ".join(default.split())
                style.setdefault(key, {}).update(text="" if same else text,
                                                 status="configured" if text and not same else "not_configured")
            save_json(path, voice)
            self.log("prompts_saved", reference="comuns")

    def save_property(self, fields, first_read_days=None):
        """Create or update a property from listing data; the facts go to its knowledge base. A new property's
        first read goes back first_read_days (asked when it is created; FIRST_READ_DAYS by default)."""
        fields = clean_property(fields)
        back = FIRST_READ_DAYS if first_read_days in (None, "") else first_read_days
        if isinstance(back, bool) or not isinstance(back, int) or not FIRST_READ_RANGE[0] <= back <= FIRST_READ_RANGE[1]:
            raise ValueError("Indica os dias da primeira leitura: um número de 1 a 365.")
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
            created = ref not in profiles
            queue = self.load(ref)
            if created and not queue.get("last_read_at"):
                queue["read_from"] = (date.today() - timedelta(days=back)).isoformat()
                self.save(queue, ref)
            # 02/10: the owner's email, set or changed: what came in from them as a customer moves to their side now
            owner = str(fields.get("owner_email") or "").strip()
            if owner and self.adopt_owner(ref, queue, owner):
                self.save(queue, ref)
            self.log("property_saved", reference=ref)
            return {"reference": ref, "created": created}

    def knowledge(self, property_ref=None, owner=None):
        """What the assistant knows, exactly as it gets it: the property's base and the agency's know-how."""
        with locked(self.folder):
            profiles = self.profiles()
            # Without a property (several of them), only the agency's know-how: that is its own editor.
            ref = self.pick(profiles, property_ref) if property_ref or len(profiles) <= 1 else None
            base = property_folder(self.folder, ref) if ref else None
            files = lambda folder: [{"file": name, "text": text} for name, text in knowledge_files(folder)]
            return {"property_ref": ref, "agency": load_knowledge(self.folder),
                    "property": load_knowledge(base) if ref else [],
                    "deal": deal_of(profiles[ref]) if ref else None,
                    # The files as the owner wrote them, comments included, for editing in the page; 30/09: the
                    # agency's know-how in three — common, rentals only, sales only
                    "files": {"agency": files(self.folder), "property": files(base) if ref else [],
                              **{f"agency-{deal}": files(self.folder / deal) for deal in DEALS},
                              "owners": files(self.folder / OWNER_FOLDER),  # 02/10: for talking to owners
                              # 02/10: this property's owner's own knowledge (only in the replies to them)
                              "owner": files(owner_folder(self.folder, owner)) if (owner := owner or ((profiles.get(ref) or {})
                                                                                   .get("property") or {}).get("owner_email")) else []}}

    def save_knowledge(self, property_ref, file, text, scope="property", owner=None):
        """Writes one knowledge (RAG) file, whole. An empty text leaves the file empty, so it no longer counts."""
        file, text = str(file or "").strip(), str(text or "").replace("\r\n", "\n")
        if not KNOWLEDGE_FILE.fullmatch(file):
            raise ValueError("O nome do ficheiro só pode ter letras, algarismos, _ e -, e acabar em .md.")
        if scope not in ("property", "agency", "owners", "owner", *(f"agency-{deal}" for deal in DEALS)):
            raise ValueError("Escolhe onde guardar: neste imóvel ou para todos.")
        with locked(self.folder):
            profiles = self.profiles()
            owner = str(owner or "").strip().casefold() if scope == "owner" else None
            if owner and owner not in self.owner_index(profiles):
                raise ValueError("Esse email não está na lista de proprietários.")
            ref = self.pick(profiles, property_ref) if scope == "property" or (scope == "owner" and not owner) else None
            if scope == "property" and not ref:
                raise ValueError("Esta pasta não tem imóveis.")
            if scope == "owner" and not owner:
                owner = ((profiles.get(ref) or {}).get("property") or {}).get("owner_email")
                if not owner:
                    raise ValueError("Este imóvel ainda não tem o email do proprietário.")
                ref = None
            # 30/09: the agency's rentals-only or sales-only know-how lives in data/<deal>/knowledge/
            base = (owner_folder(self.folder, owner) if owner else property_folder(self.folder, ref) if ref
                    else self.folder / OWNER_FOLDER if scope == "owners"
                    else self.folder / scope.split("-", 1)[1] if "-" in scope else self.folder)
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
        if scope not in ("property", "agency", "agency-deal"):
            raise ValueError("Escolhe onde guardar: neste imóvel ou para todos.")
        with locked(self.folder):
            profiles = self.profiles()
            ref = self.pick(profiles, property_ref) if scope in ("property", "agency-deal") else None
            if scope in ("property", "agency-deal") and not ref:
                raise ValueError("Esta pasta não tem imóveis.")
            # 30/09: «agency-deal»: every property of this one's kind (rentals or sales), in data/<deal>/knowledge/
            base = (self.folder / deal_of(profiles[ref]) if scope == "agency-deal"
                    else property_folder(self.folder, ref) if ref else self.folder)
            add_note(base, text, date.today())
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
