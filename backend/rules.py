"""Rules of the property workflow: one email family, one queue and one conversation log per property.

Which property an email belongs to, what to extract from it, who may receive the reply, and the checks
on profiles, voice and listing data. Pure functions: no files, network or clock. The files are read by
store.py; the instructions for the assistant are in ai.py.
"""
import base64
import copy
import re
from urllib.parse import urlsplit

REFERENCE = re.compile(r"[A-Za-z0-9_-]{1,64}")
EMAIL = re.compile(r"[^@\s<>(),;:\"\[\]]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
PHONE = re.compile(r"\+?\d[\d .()-]{7,}\d")
LISTING = re.compile(r"Código do anúncio:\s*(\d+)")
SUBJECT_NAME = re.compile(r"\bde (.+?) sobre o teu imóvel")
QUOTE = re.compile(r"^(>|(Em|On|No dia) .+(escreveu|wrote):?$|_{10,}$|-{3,} ?(Original Message|Mensagem original))")
KNOWLEDGE_LIMIT = 30000
COMMENT = re.compile(r"<!--.*?-->", re.S)
# The subject of a reply to a portal lead, until the owner writes another one in voice.json.
SUBJECT_DEFAULT = "{imovel}"
IDEALISTA_LINK = re.compile(r"https://(?:www\.)?idealista\.pt/(?:imovel/)?(\d+)/?(?:[?#].*)?")
# The property's photo is the owner's own file: the portal blocks robots, so it is never fetched.
PHOTO_LIMIT = 3 * 1024 * 1024
PHOTO_KINDS = {b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png"}


def photo_of(data_url):
    """(kind, bytes) of an uploaded photo, checked by its first bytes and not by what the browser claims."""
    header, _, payload = str(data_url or "").partition(",")
    if not header.startswith("data:image/") or not header.endswith(";base64"):
        raise ValueError("Escolhe uma fotografia (JPG, PNG ou WebP).")
    try:
        data = base64.b64decode(payload, validate=True)
    except ValueError:
        raise ValueError("A fotografia chegou incompleta; tenta outra vez.") from None
    if len(data) > PHOTO_LIMIT:
        raise ValueError("A fotografia é demasiado grande (máximo 3 MB).")
    kind = next((kind for magic, kind in PHOTO_KINDS.items() if data.startswith(magic)), None)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = "webp"
    if not kind:
        raise ValueError("O ficheiro não é uma fotografia JPG, PNG ou WebP.")
    return kind, data


def drop_empty_sections(text):
    """Remove headings with nothing under them, e.g. untouched sections of the starter file."""
    lines = text.strip().splitlines()
    def level(line):
        return len(line) - len(line.lstrip("#"))
    keep = []
    for i, line in enumerate(lines):
        if line.startswith("#"):
            following = next((other for other in lines[i + 1:] if other.strip()), None)
            if following is None or (following.startswith("#") and level(following) <= level(line)):
                continue
        keep.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).strip()


def knowledge(files):
    """The property's RAG base from its knowledge files, given as (name, text) pairs in name order.

    HTML comments and empty sections are dropped; a file with only headings left is skipped.
    """
    parts = []
    for name, text in files:
        text = drop_empty_sections(COMMENT.sub("", text))
        if any(line.strip() and not line.startswith("#") for line in text.splitlines()):
            parts.append({"file": name, "text": text})
    size = sum(len(part["text"]) for part in parts)
    if size > KNOWLEDGE_LIMIT:
        raise ValueError(f"a base de conhecimento tem {size} caracteres; o limite é {KNOWLEDGE_LIMIT}. Resume os ficheiros.")
    return parts


def check_profile(ref, profile, account):
    match = profile.get("match", {})
    if (not REFERENCE.fullmatch(ref) or profile.get("property", {}).get("reference") != ref
            or not match.get("from_address_equals") or not match.get("subject_property_reference_equals")):
        raise ValueError(f"Perfil inválido: properties/{ref}/profile.json")
    if str(profile.get("account", "")).casefold() != account.casefold():
        raise ValueError(f"O perfil {ref} pertence a outra conta.")


def parse_rent(value):
    """Monthly euros from a number or text such as "1.500 €", "1 500,50", "1,500.00" or "850.00".

    The last separator is the decimal one when one or two digits follow it; any other separator
    groups thousands. Ambiguous text is refused, not guessed: the owner then types the value.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Renda inválida.")
    if not isinstance(value, str):
        return float(value)
    numbers = re.findall(r"\d(?:[\d.,\s]*\d)?", value)
    if not numbers:
        return None
    if len(numbers) > 1:
        raise ValueError("Renda ambígua: indica só o valor mensal.")
    text = re.sub(r"\s", "", numbers[0])
    whole, decimals = text, ""
    last = max(text.rfind("."), text.rfind(","))
    if last >= 0 and len(text) - last - 1 in (1, 2):
        whole, decimals = text[:last], text[last + 1:]
    if not re.fullmatch(r"\d+|\d{1,3}([.,])\d{3}(?:\1\d{3})*", whole):
        raise ValueError("Renda inválida: escreve, por exemplo, 1500 ou 1.500,50.")
    return float(re.sub(r"\D", "", whole) + (f".{decimals}" if decimals else ""))


def clean_property(fields):
    """Listing data typed by the owner or pasted from ChatGPT: plain values of bounded size."""
    if not isinstance(fields, dict):
        raise ValueError("Esperava um objeto com os dados do imóvel.")
    clean = {}
    for key, limit in (("reference", 64), ("sender", 200), ("listing_id", 20), ("listing_url", 300),
                       ("advertiser", 100), ("description", 200)):
        value = fields.get(key)
        if value is not None and not isinstance(value, (str, int)) or len(str(value or "")) > limit:
            raise ValueError(f"Campo inválido: {key}")
        clean[key] = " ".join(str(value or "").split()) or None
    if clean["reference"] and not REFERENCE.fullmatch(clean["reference"]):
        raise ValueError("A referência só pode ter letras, algarismos, _ e - (ex.: AP_T3_LISBOA).")
    if clean["sender"] and not EMAIL.fullmatch(clean["sender"]):
        raise ValueError("O remetente dos avisos tem de ser um endereço de email.")
    if clean["listing_id"] and not clean["listing_id"].isdigit():
        raise ValueError("O código do anúncio tem de ter só algarismos.")
    if clean["listing_url"] and urlsplit(clean["listing_url"]).scheme != "https":
        raise ValueError("O link do anúncio tem de começar por https://.")
    idealista = IDEALISTA_LINK.fullmatch(clean["listing_url"] or "")
    if idealista:
        # One form for every Idealista link, and the listing code comes with it.
        if clean["listing_id"] and clean["listing_id"] != idealista[1]:
            raise ValueError("O código do anúncio não corresponde ao link.")
        clean["listing_id"] = idealista[1]
        clean["listing_url"] = f"https://www.idealista.pt/imovel/{idealista[1]}/"
    rent = parse_rent(fields.get("advertised_rent_eur"))
    if rent is not None and not 0 <= rent <= 1_000_000:
        raise ValueError("Renda inválida.")
    clean["advertised_rent_eur"] = int(rent) if rent is not None and rent.is_integer() else rent
    facts = fields.get("facts") or []
    facts = facts.splitlines() if isinstance(facts, str) else facts
    if (not isinstance(facts, list) or len(facts) > 40
            or any(not isinstance(fact, (str, int, float)) or len(str(fact)) > 300 for fact in facts)):
        raise ValueError("Características inválidas: até 40 linhas curtas.")
    clean["facts"] = [" ".join(str(fact).lstrip("-• ").split()) for fact in facts if str(fact).strip()]
    return clean


def build_profile(fields, account, template, existing, today):
    """A property's profile. Listing data comes from the owner or ChatGPT; the reply safety rules
    come from the template or the existing profile (None for a new one), plus the portal sender the owner typed."""
    profile = copy.deepcopy(existing or template)
    profile.pop("_knowledge", None)  # runtime only, never written to profile.json
    ref = fields["reference"]
    prop, match = profile.setdefault("property", {}), profile.setdefault("match", {})
    reply = profile.setdefault("reply", {})
    general = reply.setdefault("prompts", {}).setdefault("general", {})
    text = general.get("text") or ""
    for before, after in ((prop.get("reference"), ref), (prop.get("description"), fields["description"])):
        if before and after:
            text = text.replace(before, after)
    general["text"] = text
    if not existing:
        profile["account"] = account
        match["subject_property_reference_equals"] = ref
    sender = fields.get("sender") or match.get("from_address_equals")
    match.update(from_address_equals=sender, if_body_listing_id_present_must_equal=fields["listing_id"])
    kept = reply.get("never_reply_to") or [] if existing else []
    reply["never_reply_to"] = list(dict.fromkeys([*kept, sender, account]))
    prop.update({key: fields[key] for key in ("reference", "listing_id", "listing_url", "advertiser",
                                              "description", "advertised_rent_eur")})
    prop["information_source"] = f"Página local, {today.isoformat()}"
    return profile


def check_voice(voice):
    """The shared voice is mandatory once there are properties: without it nothing starts."""
    style = voice.get("style") or {}
    missing = [label for key, label in (("greeting", "saudação"), ("languages", "idiomas"), ("closing", "fecho"))
               if (style.get(key) or {}).get("selected") not in ((style.get(key) or {}).get("options") or {})]
    if not str((style.get("signature") or {}).get("text", "")).strip():
        missing.append("assinatura")
    if missing:
        raise ValueError("Configura a voz em voice.json antes de usar (falta: " + ", ".join(missing) + ").")
    return voice


def subject_of(kind, template, profile):
    """The subject the customer sees, or None to keep answering under their own subject.

    A portal lead is our first email to that person: the portal's subject was written for the owner
    (emoji, internal reference, advertiser), so it names the property instead. A direct reply from the
    customer keeps their subject, so the conversation stays together.
    """
    if kind != "lead":
        return None
    prop = profile.get("property", {})
    text = str(template or SUBJECT_DEFAULT)
    for token, value in (("{imovel}", prop.get("description")), ("{referencia}", prop.get("reference"))):
        text = text.replace(token, str(value or "").strip())
    return " ".join(text.split())[:200] or None


def addresses(values):
    return [str(a.get("email", "")).strip() for a in values or [] if str(a.get("email", "")).strip()]


def has_token(text, token):
    return re.search(rf"(?<![\w-]){re.escape(token)}(?![\w-])", text or "") is not None


def route(item, profiles, queues):
    """Return (ref, kind, customer); kind is lead, follow_up, ambiguous or None (not ours)."""
    senders = {a.casefold() for a in addresses(item.get("from"))}
    leads = [ref for ref, profile in profiles.items()
             if senders == {profile["match"]["from_address_equals"].casefold()}
             and has_token(item.get("subject", ""), profile["match"]["subject_property_reference_equals"])]
    if leads:
        return (leads[0], "lead", None) if len(leads) == 1 else (None, "ambiguous", None)
    # Customers answer from their own address: link them by our sent Message-IDs or the Gmail thread.
    ids = set(f'{item.get("in_reply_to", "")} {item.get("references", "")}'.split())
    thread = item.get("thread_id")
    found = {(ref, customer) for ref, data in queues.items()
             for customer, conversation in data.get("conversations", {}).items()
             if ids & set(conversation.get("sent_message_ids", []))
             or (thread and thread in conversation.get("thread_ids", []))}
    if len(found) == 1:
        ref, customer = found.pop()
        return ref, "follow_up", customer
    return (None, "ambiguous", None) if found else (None, None, None)


def prepare(item, kind, customer, profile, account):
    """Extract the customer and fix the only allowed recipient, once, at READ time."""
    reply = profile.get("reply", {})
    never = {a.casefold() for a in reply.get("never_reply_to", [])} | {account.casefold()}
    lines = [line.strip() for line in str(item.get("body_text", "")).splitlines() if line.strip()]
    warnings, blocked, recipient = [], None, None
    if kind == "follow_up":
        senders = item.get("from") or []
        email = addresses(senders)[0] if len(addresses(senders)) == 1 else None
        name = str(senders[0].get("name", "")).strip() if len(senders) == 1 else ""
        cut = next((i for i, line in enumerate(lines) if QUOTE.match(line)), len(lines))
        if email and email.casefold() == customer and email.casefold() not in never:
            recipient = {"name": name, "email": email}
        else:
            blocked = "Conversa ambígua: o remetente não é o cliente desta conversa. Confirma manualmente."
        fields = {"name": name or None, "email": email, "phone": None, "message": "\n".join(lines[:cut]) or None}
        return {"customer": fields, "recipient": recipient, "blocked": blocked, "warnings": warnings}

    # Portal notice: contact lines, then the customer's message, then "Ref. ..." and portal boilerplate.
    end = next((i for i, line in enumerate(lines) if line.startswith("Ref.") or LISTING.search(line)), None)
    head = lines[:end] if end is not None else lines
    email_at = next((i for i, line in enumerate(head) if EMAIL.fullmatch(line)), None)
    phone_at = next((i for i, line in enumerate(head)
                     if PHONE.fullmatch(line) and sum(c.isdigit() for c in line) >= 9), None)
    contact = [i for i in (email_at, phone_at) if i is not None]
    name = SUBJECT_NAME.search(item.get("subject", ""))
    if name:
        name = name[1].strip()
    elif contact and min(contact) > 0 and not re.search(r"[\d@]", head[min(contact) - 1]):
        name = head[min(contact) - 1]
    else:
        name = None
    message = "\n".join(head[max(contact) + 1:]) if contact and end is not None else ""

    reply_to = item.get("reply_to") or []
    valid = [a for a in reply_to if EMAIL.fullmatch(str(a.get("email", "")).strip())]
    if not reply_to:
        blocked = reply.get("missing_reply_to_notice") or "Sem Reply-To: confirma o destinatário."
    elif len(reply_to) != 1 or len(valid) != 1 or valid[0]["email"].strip().casefold() in never:
        blocked = reply.get("invalid_reply_to_notice") or "Reply-To inválido: confirma o destinatário."
    else:
        recipient = {"name": str(valid[0].get("name", "")).strip(), "email": valid[0]["email"].strip()}

    body_email = head[email_at] if email_at is not None else None
    if recipient and body_email and body_email.casefold() != recipient["email"].casefold():
        warnings.append(f"O email no corpo ({body_email}) difere do Reply-To; confirma o contacto.")
    listing = LISTING.search(str(item.get("body_text", "")))
    expected = str(profile.get("match", {}).get("if_body_listing_id_present_must_equal") or "")
    if listing and expected and listing[1] != expected:
        warnings.append(f"O código do anúncio no email ({listing[1]}) difere do perfil ({expected}).")
    if not message:
        warnings.append("Não identifiquei a mensagem do cliente; lê body_text.")
    fields = {"name": name, "email": recipient["email"] if recipient else None,
              "phone": head[phone_at] if phone_at is not None else None, "message": message or None}
    return {"customer": fields, "recipient": recipient, "blocked": blocked, "warnings": warnings}


# Visits: the owner proposes a day and a time window; slots start every `slot` minutes from its start.
VISIT_SLOT_DEFAULT = 30
KNOWLEDGE_FILE = re.compile(r"[A-Za-z0-9_-]{1,40}\.md")
VISIT_STATES = {"nao_quer": "não quer visitar", "outra_data": "só pode noutra data"}
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
CLOCK = re.compile(r"([01]\d|2[0-3]):[0-5]\d")
RGPD_STATES = {"por_pedir": "por pedir", "pedido": "pedido", "sim": "sim", "nao": "não"}
# A reply to the consent request: the customer's own words, checked only for a leading yes.
CONSENT_YES = re.compile(r"^\s*(sim|yes|oui)\b", re.I)


def consent_yes(text):
    return bool(CONSENT_YES.match(str(text or "")))


def minutes(clock):
    hours, mins = clock.split(":")
    return int(hours) * 60 + int(mins)


def check_window(day, start, end):
    """A proposed visit window: one day, from start to end, as typed by the owner (YYYY-MM-DD, HH:MM)."""
    day, start, end = (str(value or "").strip() for value in (day, start, end))
    if not DAY.fullmatch(day) or not CLOCK.fullmatch(start) or not CLOCK.fullmatch(end):
        raise ValueError("Indica o dia (AAAA-MM-DD) e as horas de início e de fim (HH:MM).")
    if minutes(end) <= minutes(start):
        raise ValueError("A hora de fim tem de ser depois da hora de início.")
    return {"day": day, "start": start, "end": end}


def visit_times(window, slot):
    """The start times inside a window, every `slot` minutes: 17:00, 17:30… (the last one starts before the end)."""
    first, last = minutes(window["start"]), minutes(window["end"])
    return [f"{value // 60:02d}:{value % 60:02d}" for value in range(first, last, max(5, int(slot)))]


def free_times(window, slot, booked):
    """The window's times that nobody has yet; booked holds "YYYY-MM-DD HH:MM" values."""
    return [time for time in visit_times(window, slot) if f"{window['day']} {time}" not in booked]


def check_slot(value, windows, slot, booked):
    """A visit time the assistant proposed: on a window's grid and still free. Returns the window."""
    value = " ".join(str(value or "").split())
    day, _, time = value.partition(" ")
    for window in windows:
        if window["day"] == day and time in visit_times(window, slot):
            if value in booked:
                raise ValueError(f"A hora {time} de {day} já está marcada para outra pessoa.")
            return window
    raise ValueError(f"A hora «{value}» não está em nenhum intervalo proposto (de {slot} em {slot} minutos).")
