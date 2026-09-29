"""The test platform (29/09, Oficina): fictitious customers for the test property, written by the AI, whose emails are
real — they go through Gmail and come back in by «Ler emails», like any portal notice.

Gmail keeps no sender other than the account's own, so every test email leaves from the account itself with the
X-ARIA-Teste header (mail.TEST_HEADER); who the customer is goes in the Reply-To, a «+cdN» address of the same account,
which Gmail delivers back to this inbox. Only a property marked "test" reads them, and a real one never does.
«Human contest»: each notice also goes, as a separate copy, to a consultant's own email, who answers it by hand side
by side; that copy is marked apart and never read back by the page.

Nothing here goes to anyone but the account itself and the consultant's address the owner typed. The customers'
hidden profiles stay in <folder>/teste/clientes.json, never in Git.
"""
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from .ai import extract_json
from .mail import TEST_HEADER
from .openai_client import complete, estimate_cost_usd
from .rules import EMAIL
from .secrets import app_password, openai_api_key
from .store import load_contacts, load_json, locked, save_contacts, save_json, save_visits

MAX_NEW = 20  # customers per click
NEW_PERCENT = 10  # 29/09: the new customers per round of «Avançar o teste», as a share of those already in; editable
LANGUAGES = "cerca de metade em português de Portugal, alguns em português do Brasil, um quarto em inglês e um ou outro " \
            "noutra língua (francês, alemão, italiano, ucraniano, urdu…)"


def client_address(account, number):
    """The Nth test customer's address: owner+cd7@example.com for owner@example.com, delivered to the account's own inbox."""
    local, _, domain = account.partition("@")
    return f"{local.split('+')[0]}+cd{number}@{domain}"


def clients_prompt(profile, knowledge, count, known_names):
    prop = profile.get("property") or {}
    facts = "\n".join(part["text"] for part in knowledge)[:6000]
    return "\n".join([
        f"Inventa {count} interessado(s) fictício(s) em arrendar este imóvel, para testar um assistente que responde aos "
        "contactos de um portal imobiliário. Cada um é uma personagem coerente, que vai responder mais tarde aos nossos "
        "emails sempre da mesma maneira.", "",
        f"IMÓVEL: {prop.get('description')}; renda {prop.get('advertised_rent_eur')} €.", facts, "",
        "VARIEDADE (entre todos): " + LANGUAGES + "; famílias, casais, pessoas sozinhas, colegas de trabalho, estudantes; "
        "com e sem animais; alguns que arrendam por uma empresa (só alguns o dizem logo); rendimentos que chegam e que "
        "não chegam; com pressa e sem pressa; conversadores, secos, desconfiados, esquecidos (respondem só a metade); "
        "e destinos diferentes: marca e visita, desiste a meio, deixa de responder, falta à visita, pede outra data.",
        "Nomes realistas, nunca de pessoas conhecidas" + (", e diferentes destes: " + ", ".join(known_names) if known_names
                                                           else "") + ".",
        "A primeira mensagem é a que escreveria no formulário do portal: curta (1 a 4 frases), na língua dele, às vezes "
        "com perguntas sobre o imóvel, às vezes só «ainda está disponível?».", "",
        "Responde só com JSON:",
        '{"clientes": [{"nome": "<nome e apelido>", "lingua": "<pt-PT, pt-BR, en, fr…>", "mensagem": "<a primeira '
        'mensagem>", "perfil": {"trabalho": "…", "rendimento_mensal_eur": 0, "agregado": "…", "animais": "<ou nenhum>", '
        '"empresa": "<ou nenhuma>", "datas": "<entrada e duração que quer>", "disponibilidade": "<para visitas>", '
        '"feitio": "…", "segredos": "<o que só revela se lhe perguntarem>", "destino": "<como a história tende a acabar>"}}]}'])


def notice(account, ref, profile, client, to=None, consultant=False):
    """One portal notice, as the Idealista writes it, from the account itself with the test mark."""
    prop = profile.get("property") or {}
    msg = EmailMessage()
    msg["From"] = formataddr(("idealista (teste)", account))
    msg["To"] = to or account
    msg["Reply-To"] = formataddr((client["name"], client["address"]))
    subject = f"Mensagem de teste de {client['name']} sobre o teu imóvel, com ref: {ref}"
    msg["Subject"] = ("[consultor] " if consultant else "") + subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    # The page reads its own copy ("1"); the consultant's copy is marked apart and never read back.
    msg[TEST_HEADER] = "consultor" if consultant else "1"
    rent = prop.get("advertised_rent_eur")
    msg.set_content("\n".join([
        "Tens uma nova mensagem que aguarda resposta", client["name"], client["phone"], client["address"],
        *[line for line in client["message"].splitlines() if line.strip()],
        f"Ref. {ref} | {prop.get('advertiser') or 'Anunciante'}",
        f"Código do anúncio: {prop.get('listing_id') or ''}",
        f"{rent:,} €".replace(",", ".") if isinstance(rent, (int, float)) else "",
        "Mensagem de TESTE, da plataforma de testes da ARIA."]))
    return msg


def test_property(service):
    """The test property (profile "test"), and its profile; refused without one."""
    profiles = service.profiles()
    ref = next((ref for ref, profile in profiles.items() if profile.get("test")), None)
    if not ref:
        raise ValueError("Não há imóvel de teste: cria um e marca-o como teste (\"test\": true no profile.json).")
    return ref, profiles[ref]


def load_lab(folder):
    return load_json(folder / "teste" / "clientes.json", {"clients": [], "contest": {"on": False, "email": ""}})


def save_lab(folder, lab):
    (folder / "teste").mkdir(mode=0o700, exist_ok=True)
    save_json(folder / "teste" / "clientes.json", lab)


def lab_view(service):
    """What the Oficina shows: the test property, the Human contest and the customers (never their hidden profile)."""
    lab = load_lab(service.folder)
    try:
        ref = test_property(service)[0]
    except ValueError:
        ref = None
    return {"property_ref": ref, "contest": lab.get("contest") or {"on": False, "email": ""},
            "new_percent": lab.get("new_percent", NEW_PERCENT),
            "clients": [{**{key: client.get(key) for key in ("number", "name", "language", "address", "created_at")},
                         "consultant": bool(client.get("consultant_notice_id"))} for client in lab["clients"]]}


def send_to_consultant(service):
    """Human contest: the consultant's copy of every test customer who has none yet (e.g. made with the contest off)."""
    ref, profile = test_property(service)
    account = service.config()["account"]
    with locked(service.folder, "testlab"):
        lab = load_lab(service.folder)
        contest = lab.get("contest") or {}
        if not contest.get("on") or not contest.get("email"):
            raise ValueError("Liga o Human contest e indica o email do consultor.")
        missing = [client for client in lab["clients"] if not client.get("consultant_notice_id")]
        if missing:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
                smtp.login(account, app_password(service.folder, account))
                for client in missing:
                    copy = notice(account, ref, profile, client, to=contest["email"], consultant=True)
                    smtp.send_message(copy)
                    client["consultant_notice_id"] = str(copy["Message-ID"])
                    save_lab(service.folder, lab)
        service.log("testlab_consultant", reference=ref, sent=len(missing))
    return {**lab_view(service), "sent": len(missing)}


def set_contest(service, on, email, new_percent=None):
    """The Human contest (on, the consultant's email) and, when given, the new customers' share per round."""
    email = " ".join(str(email or "").split())
    if new_percent is not None and (isinstance(new_percent, bool) or not isinstance(new_percent, int)
                                    or not 0 <= new_percent <= 100):
        raise ValueError("A percentagem de clientes novos vai de 0 a 100.")
    if on and not EMAIL.fullmatch(email):
        raise ValueError("Indica o email do consultor para o Human contest.")
    if email and email.casefold() == service.config()["account"].casefold():
        raise ValueError("O consultor tem de ter um email seu, não o desta conta.")
    with locked(service.folder, "testlab"):
        lab = load_lab(service.folder)
        lab["contest"] = {"on": bool(on), "email": email}
        if new_percent is not None:
            lab["new_percent"] = new_percent
        save_lab(service.folder, lab)
    return lab_view(service)


def generate_clients(service, count, now):
    """«Gerar clientes de teste»: the AI invents count customers; each one's notice goes out, and to the consultant
    too with the Human contest on. Returns the page's view and the call's cost."""
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= MAX_NEW:
        raise ValueError(f"Indica quantos clientes: de 1 a {MAX_NEW}.")
    ref, profile = test_property(service)
    service.require_fuel(ref)
    cfg = service.config()
    account, model = cfg["account"], service.model(cfg)
    with locked(service.folder, "testlab"):
        lab = load_lab(service.folder)
        prompt = clients_prompt(profile, profile.get("_knowledge") or [], count, [c["name"] for c in lab["clients"]])
        answer, usage = complete(openai_api_key(service.folder, account), model, prompt)
        cost = estimate_cost_usd(model, usage.get("prompt_tokens"), usage.get("completion_tokens"))
        service.log("openai_usage", model=model, **usage, reference=ref, cost_usd=round(cost, 6))
        found = extract_json(answer)
        invented = [item for item in (found.get("clientes") if isinstance(found, dict) else None) or []
                    if isinstance(item, dict) and str(item.get("nome") or "").strip() and str(item.get("mensagem") or "").strip()]
        if not invented:
            raise ValueError("A IA não devolveu clientes: tenta de novo.")
        contest = lab.get("contest") or {}
        consultant = contest.get("email") if contest.get("on") else None
        # never a number used before, not even by customers already wiped (their emails are still in the inbox)
        start = max([client["number"] for client in lab["clients"]] + [lab.get("next_number", 1) - 1]) + 1
        made = []
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(account, app_password(service.folder, account))
            for offset, item in enumerate(invented[:count]):
                number = start + offset
                client = {"number": number, "name": " ".join(str(item["nome"]).split())[:80],
                          "language": str(item.get("lingua") or "")[:12], "address": client_address(account, number),
                          "phone": f"900 000 {number:03d}", "message": str(item["mensagem"]).strip()[:1500],
                          "profile": item.get("perfil") if isinstance(item.get("perfil"), dict) else {},
                          "created_at": now}
                sent = notice(account, ref, profile, client)
                smtp.send_message(sent)
                client["notice_id"] = str(sent["Message-ID"])
                if consultant:
                    copy = notice(account, ref, profile, client, to=consultant, consultant=True)
                    smtp.send_message(copy)
                    client["consultant_notice_id"] = str(copy["Message-ID"])
                lab["clients"].append(client)
                lab["next_number"] = number + 1
                made.append(client["name"])
                save_lab(service.folder, lab)  # after each one: a failure midway never forgets who already went
        service.log("testlab_clients", reference=ref, created=len(made), contest=bool(consultant))
    return {**lab_view(service), "created": made, "cost_usd": round(cost, 6), "fuel": service.api_fuel(ref)}


def wipe(service):
    """«Apagar clientes de teste»: the test property starts over — its queue, conversations, agenda and contacts, and
    the lab's customers. The emails stay in Gmail: their IDs are kept as dismissed, so no read brings them back."""
    ref, _ = test_property(service)
    with locked(service.folder):
        data = service.load(ref)
        data["dismissed_message_ids"].extend(key for item in data["emails"] for key in (item["id"], *item.get("merged_ids", [])))
        conversations = len(data.get("conversations") or {})
        data["emails"], data["conversations"] = [], {}
        data.pop("send_preview", None)
        service.save(data, ref)
        save_visits(service.folder, ref, {"windows": [], "slots": [], "closed_at": None})
        contacts = load_contacts(service.folder)
        save_contacts(service.folder, {key: row for key, row in contacts.items() if key[1] != ref})
    with locked(service.folder, "testlab"):
        lab = load_lab(service.folder)
        removed = len(lab["clients"])
        lab["next_number"] = max([client["number"] for client in lab["clients"]] + [lab.get("next_number", 1) - 1]) + 1
        lab["clients"] = []
        save_lab(service.folder, lab)
    service.log("testlab_wiped", reference=ref, clients=removed, conversations=conversations)
    return {**lab_view(service), "removed": removed}
