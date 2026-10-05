"""Rules of the property workflow: one email family, one queue and one conversation log per property.

Which property an email belongs to, what to extract from it, who may receive the reply, and the checks
on profiles, voice and listing data. Pure functions: no files, network or clock. The files are read by
store.py; the instructions for the assistant are in ai.py.
"""
import base64
import copy
import re
from urllib.parse import urlsplit
from . import portals

REFERENCE = re.compile(r"[A-Za-z0-9_-]{1,64}")
EMAIL = re.compile(r"[^@\s<>(),;:\"\[\]]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
PHONE = re.compile(r"\+?\d[\d .()-]{7,}\d")
# 27/09: a phone a customer wrote in a message, for the page's WhatsApp button only: a Portuguese mobile, with or without
# +351, or a number written with its country code (+… or 00…). Dates, prices and references do not match.
MESSAGE_PHONE = re.compile(r"(?<![\d+])(?:(?:\+|00)351[\s.-]?)?9[1236](?:[\s.-]?\d){7}(?!\d)"
                           r"|(?<![\d+])(?:\+|00)[1-9]\d{0,2}(?:[\s.-]?\d){6,12}(?!\d)")
QUOTE = re.compile(r"^(>|(Em|On|No dia) .+(escreveu|wrote):?$|_{10,}$|-{3,} ?(Original Message|Mensagem original))")
KNOWLEDGE_LIMIT = 30000
COMMENT = re.compile(r"<!--.*?-->", re.S)
# The subject of a reply to a portal lead, until the owner writes another one in voice.json.
SUBJECT_DEFAULT = "{imovel}"
# 02/10: what is particular to the portal (its senders, how its subject names the customer, its listing code and link,
# its call notices) lives in portals.py, changeable in the Oficina: apply_portal sets these from it.
PORTAL, LISTING, SUBJECT_NAME, IDEALISTA_LINK, CALL = {}, None, None, None, {}


def apply_portal(changes=None):
    """The portal as the Oficina left it (config.json "portal"), into the rules the reading uses."""
    global PORTAL, LISTING, SUBJECT_NAME, IDEALISTA_LINK, CALL
    PORTAL = portals.merged(changes)
    LISTING = re.compile(PORTAL["codigo_anuncio"])
    SUBJECT_NAME = re.compile(PORTAL["assunto_nome"])  # 29/09: «Mensagem de teste de X…» too
    IDEALISTA_LINK = re.compile(PORTAL["link_anuncio"])
    CALL = {key: re.compile(PORTAL[key], re.I | re.M) for key in PORTAL if key.startswith(("chamada_", "assunto_chamada"))}


def call_notice(item):
    """02/10: a portal's call notice, told by its headers alone (sender and subject), before its text is fetched."""
    senders = {address.casefold() for address in addresses(item.get("from") or [])}
    return (PORTAL["remetente_chamadas"].casefold() in senders
            and bool(CALL["assunto_chamada"].search(item.get("subject") or "")))


def phone_key(value):
    """02/10: a phone as digits to compare: a Portuguese one without its 351 (or 00351), any other with its country code."""
    digits = re.sub(r"\D", "", str(value or ""))
    digits = digits[2:] if digits.startswith("00") else digits
    return digits[3:] if len(digits) == 12 and digits.startswith("351") else digits


def parse_call(item):
    """02/10: a portal's call notice («Chamada atendida / não respondida de um interessado…»): who called (the phone,
    digits only), when (the call's own time, from the text: the email can come days later), whether it was answered,
    how long, and the listing and reference when the notice has them. None for any other email."""
    if not call_notice(item):
        return None
    body = str(item.get("body_text") or "")
    found = {key: CALL[key].search(body) for key in CALL if key != "assunto_chamada"}
    phone = re.sub(r"\D", "", found["chamada_telefone"].group(1)) if found["chamada_telefone"] else ""
    when = found["chamada_data"].group(1) if found["chamada_data"] else ""
    if not phone or not when:
        return None
    day, clock = when.split(" ", 1)
    state = found["chamada_estado"].group(1).strip() if found["chamada_estado"] else ""
    return {"phone": phone, "at": f"{day[6:10]}-{day[3:5]}-{day[0:2]} {clock}", "state": state,
            "answered": bool(CALL["chamada_atendida"].search(state)),
            "seconds": int(found["chamada_duracao"].group(1)) if found["chamada_duracao"] else None,
            "listing": found["chamada_anuncio"].group(1) if found["chamada_anuncio"] else None,
            "ref": found["chamada_ref"].group(1) if found["chamada_ref"] else None}
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


# 30/09: the two kinds of business, each with the agency's own know-how (data/arrendamento/knowledge/,
# data/venda/knowledge/), on top of the one common to all (data/knowledge/). A property without one is a rental.
DEALS = ("arrendamento", "venda")


def deal_of(profile):
    deal = (profile.get("property") or {}).get("deal")
    return deal if deal in DEALS else "arrendamento"


def check_profile(ref, profile, account):
    match = profile.get("match", {})
    if (not REFERENCE.fullmatch(ref) or profile.get("property", {}).get("reference") != ref
            or not match.get("from_address_equals") or not match.get("subject_property_reference_equals")):
        raise ValueError(f"Perfil inválido: properties/{ref}/profile.json")
    if str(profile.get("account", "")).casefold() != account.casefold():
        raise ValueError(f"O perfil {ref} pertence a outra conta.")


def property_active(profile):
    """ATIVO unless the owner set it INATIVO (26/09); a profile from before then has no field and is active."""
    return profile.get("active") is not False


# The customer's file (26/09): what the qualification (the 2nd interaction, repeated until a visit is proposed)
# gathers. The first four always count; the company and the pets only when the customer brought them up.
FICHA_FIELDS = {"trabalho": "Situação profissional e rendimentos", "agregado": "Agregado familiar",
                "datas": "Datas ou duração do contrato", "disponibilidade": "Disponibilidade para visitas",
                "empresa": "Empresa (se arrenda por uma)", "animais": "Animais (qual, tamanho, quantos)"}
FICHA_REQUIRED = ("trabalho", "agregado", "datas", "disponibilidade")
FICHA_OPTIONAL = ("empresa", "animais")
FICHA_VALUE_MAX = 300


def clean_ficha(raw):
    """The assistant's file for one customer: short plain texts, and which optional points it says are missing."""
    if not isinstance(raw, dict):
        return None
    ficha = {key: " ".join(str(raw[key]).split())[:FICHA_VALUE_MAX] for key in FICHA_FIELDS
             if isinstance(raw.get(key), (str, int, float)) and not isinstance(raw.get(key), bool)
             and str(raw[key]).strip() and str(raw[key]).strip().casefold() not in ("null", "none", "-", "?")}
    missing = raw.get("falta") if isinstance(raw.get("falta"), list) else []
    ficha["falta_extra"] = [key for key in FICHA_OPTIONAL if key in missing and key not in ficha]
    return ficha


def merge_ficha(old, new):
    """What we knew, with what the customer just told us on top; nothing known is ever lost to a blank."""
    merged = {key: value for key, value in (old or {}).items() if key in FICHA_FIELDS}
    merged.update({key: value for key, value in (new or {}).items() if key in FICHA_FIELDS})
    extra = (new or {}).get("falta_extra", (old or {}).get("falta_extra")) or []
    merged["falta_extra"] = [key for key in FICHA_OPTIONAL if key in extra and key not in merged]
    return merged


def ficha_summary(ficha):
    """What is still missing, and whether the file is complete (the four required points and any optional
    one the customer raised)."""
    ficha = ficha or {}
    missing = [key for key in FICHA_REQUIRED if not ficha.get(key)] + list(ficha.get("falta_extra") or [])
    return {"falta": missing, "complete": not missing,
            "known": sum(1 for key in FICHA_REQUIRED if ficha.get(key)), "total": len(FICHA_REQUIRED)}


# The after-visit survey (26/09): the three parts asked, each read on its own dial. A 1 weighs three times and a 2
# twice as much as a 3, 4 or 5, so a few very bad answers pull the dial down hard; all 1s read 0, all 5s 100.
SURVEY_PARTS = {"imovel": "Imóvel", "consultor": "Consultor", "marcacao": "Marcação e emails"}
SCORE_WEIGHTS = {1: 3, 2: 2, 3: 1, 4: 1, 5: 1}
QUALITY_GREEN = 80  # at or above: excellent (the dial's green)
QUALITY_RED = 40    # below: the dial's red


def quality(scores):
    """0 to 100 from 1-to-5 answers, weighted so the 1s and 2s count more; None without answers."""
    scores = [score for score in scores if score in SCORE_WEIGHTS]
    if not scores:
        return None
    weight = sum(SCORE_WEIGHTS[score] for score in scores)
    return round(sum(SCORE_WEIGHTS[score] * (score - 1) * 25 for score in scores) / weight)


def survey_alerts(survey):
    """What in a survey answer the owner must see: a 1 or a 2, or «não» to still being interested."""
    survey = survey or {}
    alerts = [f"{label}: {survey[part]}/5" for part, label in SURVEY_PARTS.items() if survey.get(part) in (1, 2)]
    if survey.get("interesse") == "não":
        alerts.append("já não tem interesse")
    return alerts


def survey_report(surveys):
    """The dials and the detail for a set of survey answers: one dial per part, interest and comments."""
    surveys = [survey for survey in surveys if survey]
    parts = {}
    for part, label in SURVEY_PARTS.items():
        scores = [survey.get(part) for survey in surveys if survey.get(part) in SCORE_WEIGHTS]
        parts[part] = {"label": label, "score": quality(scores), "count": len(scores),
                       "average": round(sum(scores) / len(scores), 1) if scores else None,
                       "ones": scores.count(1)}
    interest = {key: sum(1 for survey in surveys if survey.get("interesse") == key) for key in ("sim", "talvez", "não")}
    # The fourth dial (26/09): still interested in renting — «sim» 100, «talvez» 50, «não» 0, averaged.
    answered = interest["sim"] + interest["talvez"] + interest["não"]
    parts["interesse"] = {"label": "Interesse em arrendar", "count": answered, "average": None, "ones": 0, "no": interest["não"],
                          "score": round((100 * interest["sim"] + 50 * interest["talvez"]) / answered) if answered else None}
    return {"responses": len(surveys), "parts": parts, "interest": interest,
            "alerts": sum(1 for survey in surveys if survey_alerts(survey)), "green": QUALITY_GREEN, "red": QUALITY_RED}


# The selection (26/09): 2 or 3 candidates on a short list; one chosen and one reserve (suplente). The documents are
# asked only of the short list, and the program keeps a checklist of what arrived, never the files themselves.
SELECTION_STATES = {"shortlist": "Short list", "chosen": "Selecionado", "suplente": "Suplente"}  # 04/10: «Escolhido» → «Selecionado»
DOCUMENTS = {"recibos": ("Recibos de vencimento", True), "email_emprego": ("Email oficial do emprego (se tiver)", False),
             "contrato": ("Declaração ou contrato de trabalho (opcional)", False),
             "irs": ("IRS do ano anterior (ou dos dois anteriores)", True)}


def documents_summary(selection):
    """Which documents arrived, for the candidate and, when there is one, the guarantor (fiador)."""
    selection = selection or {}
    received = selection.get("docs") or {}
    people = ["candidato"] + (["fiador"] if selection.get("fiador") else [])
    missing = [f"{DOCUMENTS[key][0]}{' do fiador' if who == 'fiador' else ''}" for who in people
               for key, (_, required) in DOCUMENTS.items() if required and not received.get(f"{who}:{key}")]
    return {"received": received, "fiador": bool(selection.get("fiador")), "missing": missing, "complete": not missing}


PLACEHOLDER = re.compile(r"<[^<>\n@]{2,40}>")


def draft_checks(text, signature="", house_line=False, visit_slot=None):
    """What the program checks in a draft before it goes (26/09): the voice's signature once, no <field> left from a
    template, the 🏠 line when the agency's know-how asks for it, and a booked time written in the text."""
    text = str(text or "")
    if not text.strip():
        return []
    found = []
    signature = " ".join(str(signature or "").split())
    if signature and " ".join(text.split()).count(signature) != 1:
        found.append("A assinatura da voz devia aparecer uma vez, exatamente como está em Voz e estilo.")
    left = PLACEHOLDER.findall(text)
    if left:
        found.append("Ficou por preencher: " + ", ".join(dict.fromkeys(left)) + ".")
    if house_line and "🏠" not in text:
        found.append("Falta a linha 🏠 com o imóvel e o link, que o know-how pede em todas as respostas.")
    if visit_slot and str(visit_slot).split(" ")[-1] not in text:
        found.append(f"A visita marcada ({visit_slot}) não aparece no texto.")
    return found


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
    if "owner_email" in fields:
        # 27/09: who gets the property's report (the ponto de situação). Only when the form sends it: other callers
        # (the listing's extraction) never wipe the one already saved.
        owner = " ".join(str(fields.get("owner_email") or "").split())
        if owner and (len(owner) > 200 or not EMAIL.fullmatch(owner)):
            raise ValueError("O email do proprietário tem de ser um endereço de email.")
        clean["owner_email"] = owner or None
    if "deal" in fields:
        # 30/09: arrendamento or venda — which of the agency's two know-hows the property gets
        deal = str(fields.get("deal") or "arrendamento").strip().lower()
        if deal not in DEALS:
            raise ValueError("O tipo de negócio é arrendamento ou venda.")
        clean["deal"] = deal
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
        clean["listing_url"] = PORTAL["link_anuncio_forma"].replace("{codigo}", idealista[1])
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
    if not existing:
        profile.pop("active", None)  # a new property starts ATIVO, even when its template is INATIVO
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
                                              "description", "advertised_rent_eur", "owner_email", "deal") if key in fields})
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


def phone_in(text):
    """The first phone a customer wrote in a message (see MESSAGE_PHONE), as written; "" when there is none."""
    match = MESSAGE_PHONE.search(str(text or ""))
    return match.group(0).strip() if match else ""


def route(item, profiles, queues):
    """Return (ref, kind, customer); kind is lead, follow_up, ambiguous or None (not ours)."""
    senders = {a.casefold() for a in addresses(item.get("from"))}
    # 29/09: a test property (profile "test") takes only the test platform's notices, and a real one never does
    leads = [ref for ref, profile in profiles.items()
             if bool(profile.get("test")) == bool(item.get("test"))
             and senders == {profile["match"]["from_address_equals"].casefold()}
             and has_token(item.get("subject", ""), profile["match"]["subject_property_reference_equals"])]
    if leads:
        return (leads[0], "lead", None) if len(leads) == 1 else (None, "ambiguous", None)
    # Customers answer from their own address: link them by our sent Message-IDs or the Gmail thread.
    ids = set(f'{item.get("in_reply_to", "")} {item.get("references", "")}'.split())
    thread = item.get("thread_id")
    found = {(ref, customer) for ref, data in queues.items()
             # a test platform's message never reaches a real property's conversation
             if not item.get("test") or (profiles.get(ref) or {}).get("test")
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
        # 29/09: a test customer's reply leaves from this account too; who they are is in the Reply-To
        senders = (item.get("reply_to") if item.get("test") else item.get("from")) or []
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
    body_email = head[email_at] if email_at is not None else None
    portal_only = bool(valid) and all(str(a["email"]).strip().casefold() in never for a in valid)
    if (not reply_to or portal_only) and body_email and body_email.casefold() not in never:
        # 26/09: some portal notices come without Reply-To (or, 27/09, with the portal's own address in it) but with the
        # customer's email in the body, in the contact lines. The notice came from the portal sender (route checked it),
        # so that email is the recipient — common on Idealista, so no warning since 27/09. Without one in the body, it
        # stays blocked as before.
        recipient = {"name": name or "", "email": body_email}
    elif not reply_to:
        blocked = reply.get("missing_reply_to_notice") or "Sem Reply-To: confirma o destinatário."
    elif len(reply_to) != 1 or len(valid) != 1 or valid[0]["email"].strip().casefold() in never:
        blocked = reply.get("invalid_reply_to_notice") or "Reply-To inválido: confirma o destinatário."
    else:
        recipient = {"name": str(valid[0].get("name", "")).strip(), "email": valid[0]["email"].strip()}

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


apply_portal()  # 02/10: the defaults until the Oficina's changes are read (MailService.config)
