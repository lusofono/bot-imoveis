"""A static demo of the page, to show and sell it without a server: a fictitious agency, sample data, and the
answer of every step recorded beforehand.

`bot-mail webdemo <pasta>` runs two weeks of a fictitious agency through the real backend (the clock, Gmail, the
OpenAI API and the SMTP are fakes), records what each API call answers before and after each step of the demo, and
writes a folder of plain files: the page as it is (frontend/), demo-api.js, which answers the page's calls from
those recordings, and demo-data.js. It goes to any HTTP server as it is (or opens from the disk). Nothing in it reads
or sends email, nor calls any AI; the page says so in a ribbon at the top.
"""
from contextlib import ExitStack
from datetime import date as real_date, datetime as real_datetime, time as day_time, timedelta
import json
import re
import shutil
import tempfile
import time as real_time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile
from .ai import short_id
from .demo import TEMPLATES
from .rules import clean_ficha
from .store import load_json, save_json

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
SHIM = Path(__file__).resolve().parent / "templates" / "webdemo"
ACCOUNT = "leads@casaexemplo.example"
AGENCY = "Casa Exemplo Imobiliária"
SIGNATURE = f"Equipa {AGENCY}"
TOKEN = "demo"
MODEL = "gpt-4o-mini"

# ---------------------------------------------------------------------------------------------------------------
# The fictitious agency: three properties and their customers. Every name, email, phone and address is invented.

PROPS = {
    "L": {"ref": "DEMO_T2_LISBOA", "desc": "Apartamento T2 com varanda em Campo de Ourique, Lisboa", "rent": 1450,
          "listing": "34500001", "address": "Rua das Flores Exemplo, 12, 3.º Esq., 1350-000 Lisboa", "km": 6,
          "facts": ["T2 com 85 m², varanda virada a sul, cozinha equipada, 3.º andar com elevador.",
                    "Sem garagem; estacionamento para residentes na rua (dístico municipal).",
                    "Animais de pequeno porte aceites.", "Contrato mínimo de 1 ano; caução de 2 rendas.",
                    "Janelas com vidro duplo recente; aquecimento por ar condicionado em todas as divisões."]},
    "P": {"ref": "DEMO_T1_PORTO", "desc": "Apartamento T1 renovado no Bonfim, Porto", "rent": 950, "listing": "34500002",
          "address": "Rua do Jardim Exemplo, 45, 2.º, 4000-000 Porto", "km": 4,
          "facts": ["T1 com 52 m², totalmente renovado em 2025, entregue mobilado e equipado.",
                    "A 5 minutos a pé do metro (linha que serve o Hospital de São João em 15 minutos).",
                    "Estudantes aceites com fiador.", "Contrato mínimo de 1 ano; caução de 2 rendas."]},
    "C": {"ref": "DEMO_T3_CASCAIS", "desc": "Moradia T3 com jardim no Estoril, Cascais", "rent": 2600,
          "listing": "34500003", "address": "Avenida do Mar Exemplo, 8, 2765-000 Estoril", "km": 22,
          "facts": ["Moradia T3 com 180 m² e jardim privado de 300 m².",
                    "Aquecimento central por bomba de calor e piso radiante no rés-do-chão.",
                    "Duas escolas internacionais a menos de 10 minutos de carro.", "Animais aceites.",
                    "Contrato mínimo de 2 anos; caução de 2 rendas."]}}

# key: (name, email, phone, language, gender, property)
PEOPLE = {
    "mariana": ("Mariana Costa", "mariana.costa@example.com", "+351 910 000 101", "pt", "f", "L"),
    "sophie": ("Sophie Martin", "sophie.martin@example.com", "+351 910 000 102", "fr", "f", "L"),
    "tiago": ("Tiago Rocha", "tiago.rocha@example.com", "+351 910 000 103", "pt", "m", "L"),
    "emma": ("Emma Collins", "emma.collins@example.com", "+44 7700 900104", "en", "f", "L"),
    "rafael": ("Rafael Oliveira", "rafael.oliveira@example.com", "+351 910 000 105", "pt", "m", "L"),
    "priya": ("Priya Nair", "priya.nair@example.com", "+351 910 000 106", "en", "f", "L"),
    "catarina": ("Catarina Matos", "catarina.matos@example.com", "+351 910 000 107", "pt", "f", "L"),
    "lukas": ("Lukas Weber", "lukas.weber@example.com", "+49 151 0000108", "de", "m", "L"),
    "joao": ("João Ferreira", "joao.ferreira@example.com", "+351 910 000 201", "pt", "m", "P"),
    "chloe": ("Chloé Dubois", "chloe.dubois@example.com", "+351 910 000 202", "en", "f", "P"),
    "carlos": ("Carlos Méndez", "carlos.mendez@example.com", "+34 600 000 203", "es", "m", "P"),
    "beatriz": ("Beatriz Lopes", "beatriz.lopes@example.com", "+351 910 000 204", "pt", "f", "P"),
    "miguel": ("Miguel Santos", "miguel.santos@example.com", "+351 910 000 205", "pt", "m", "P"),
    "olivia": ("Olivia Brown", "olivia.brown@example.com", "+44 7700 900301", "en", "f", "C"),
    "nuno": ("Nuno Pires", "nuno.pires@example.com", "+351 910 000 302", "pt", "m", "C"),
    "charlotte": ("Charlotte Evans", "charlotte.evans@example.com", "+31 6 0000 0303", "en", "f", "C")}


def url(prop):
    return f"https://anuncios.example/imovel/{PROPS[prop]['listing']}/"


def mark(day, lang):
    """A date in a text, written as a marker: the demo shows it in the viewer's week (demo-api.js)."""
    return f"[[D:{day}:{lang}]]"


GREET = {"pt": {"f": "Cara {first},", "m": "Caro {first},"}, "en": {"f": "Dear {first},", "m": "Dear {first},"},
         "fr": {"f": "Chère {first},", "m": "Cher {first},"}, "es": {"f": "Estimada {first},", "m": "Estimado {first},"},
         "de": {"f": "Sehr geehrte Frau {last},", "m": "Sehr geehrter Herr {last},"}}
CLOSE = {"pt": "Com os melhores cumprimentos,", "en": "Kind regards,", "fr": "Cordialement,", "es": "Un cordial saludo,",
         "de": "Mit freundlichen Grüßen,"}
BODY = {
    "first": {
        "pt": "Obrigado pelo seu contacto. O imóvel continua disponível.{extra}\n\nPara prepararmos a visita, pode "
              "dizer-nos:\n- a sua situação profissional e o rendimento mensal líquido;\n- quantas pessoas vão viver no "
              "imóvel;\n- a partir de quando pretende entrar e por quanto tempo;\n- que dias e horas lhe dão mais jeito "
              "para visitar?",
        "en": "Thank you for getting in touch. The property is still available.{extra}\n\nTo arrange a viewing, could "
              "you tell us:\n- your professional situation and monthly net income;\n- how many people would live in the "
              "property;\n- when you would like to move in and for how long;\n- which days and times suit you best for "
              "a visit?",
        "fr": "Merci pour votre message. Le bien est toujours disponible.{extra}\n\nAfin d'organiser une visite, "
              "pourriez-vous nous indiquer :\n- votre situation professionnelle et votre revenu mensuel net ;\n- le "
              "nombre de personnes qui habiteraient le logement ;\n- la date d'entrée souhaitée et la durée de la "
              "location ;\n- vos disponibilités pour une visite ?",
        "es": "Gracias por su mensaje. El inmueble sigue disponible.{extra}\n\nPara organizar la visita, ¿podría "
              "indicarnos:\n- su situación profesional y sus ingresos mensuales netos;\n- cuántas personas vivirían en "
              "la vivienda;\n- a partir de cuándo desea entrar y por cuánto tiempo;\n- qué días y horas le vienen mejor "
              "para visitar?"},
    "second": {
        "pt": "Muito obrigado pelas informações, ficam registadas.{extra} Estamos a organizar as visitas a este imóvel e "
              "voltamos ao seu contacto em breve com uma proposta de dia e hora.",
        "en": "Many thanks for the information, we have noted everything.{extra} We are organising viewings for this "
              "property and will be back in touch shortly with a proposed day and time.",
        "fr": "Merci beaucoup pour ces informations, elles sont bien notées.{extra} Nous organisons les visites de ce "
              "bien et reviendrons vers vous très prochainement avec une proposition de jour et d'horaire.",
        "es": "Muchas gracias por la información, queda registrada.{extra} Estamos organizando las visitas a este "
              "inmueble y volveremos a contactarle en breve con una propuesta de día y hora."},
    "proposal": {
        "pt": "Estamos a organizar visitas ao imóvel no dia {day}, entre as {start} e as {end}. Qual a hora que lhe dá "
              "mais jeito dentro deste intervalo? Se nenhuma lhe servir, diga-nos por favor a sua disponibilidade "
              "habitual nos dias seguintes.",
        "en": "We are organising viewings of the property on {day}, between {start} and {end}. Which time within this "
              "window suits you best? If none works, please let us know your usual availability over the following days.",
        "fr": "Nous organisons des visites du bien le {day}, entre {start} et {end}. Quel horaire vous conviendrait le "
              "mieux dans ce créneau ? Si aucun ne vous convient, merci de nous indiquer vos disponibilités habituelles "
              "les jours suivants.",
        "es": "Estamos organizando visitas al inmueble el {day}, entre las {start} y las {end}. ¿Qué hora le viene "
              "mejor dentro de este intervalo? Si ninguna le sirve, indíquenos por favor su disponibilidad habitual los "
              "días siguientes."},
    "confirm": {
        "pt": "Fica confirmada a sua visita no dia {day}, às {time}.{extra} A morada é {address}. Se não puder "
              "comparecer, pedimos-lhe que nos avise por email.",
        "en": "Your viewing is confirmed for {day} at {time}.{extra} The address is {address}. If you are unable to "
              "attend, please let us know by email.",
        "fr": "Votre visite est confirmée le {day} à {time}.{extra} L'adresse est {address}. Si vous ne pouvez pas "
              "venir, merci de nous prévenir par email.",
        "es": "Queda confirmada su visita el {day} a las {time}.{extra} La dirección es {address}. Si no pudiera "
              "asistir, le rogamos que nos avise por email."}}
SURVEY = {
    "pt": "Muito obrigado pela visita ao imóvel. {public}\n\nPara melhorarmos, pedimos-lhe um minuto: responda a este "
          "email escrevendo, à frente de cada número, uma nota de 1 (mau) a 5 (excelente).\n1. O imóvel:\n2. O "
          "consultor que o recebeu na visita:\n3. A marcação da visita e a troca de emails:\n4. Continua interessado "
          "em arrendar este imóvel? (sim / não / talvez):\n5. Comentário ou dúvida (opcional):\n\nFICHA DE VISITA\n"
          "Imóvel: {desc} (ref. {ref})\nMorada: {address}\nData e hora: {day}, {time}\nConsultor: Rui Exemplo\n"
          "Visitante: {name}\nPara ficar registada, responda também com «Confirmo a visita».",
    "fr": "Merci beaucoup pour votre visite. {public}\n\nPour nous améliorer, pourriez-vous nous accorder une minute : "
          "répondez à cet email en indiquant, après chaque numéro, une note de 1 (mauvais) à 5 (excellent).\n1. Le "
          "logement :\n2. Le conseiller qui vous a reçu :\n3. La prise de rendez-vous et les échanges d'emails :\n4. "
          "Êtes-vous toujours intéressée par ce logement ? (oui / non / peut-être) :\n5. Commentaire ou question "
          "(facultatif) :\n\nFICHE DE VISITE\nLogement : {desc} (réf. {ref})\nAdresse : {address}\nDate et heure : "
          "{day}, {time}\nConseiller : Rui Exemplo\nVisiteur : {name}\nPour l'enregistrer, répondez aussi « Je "
          "confirme la visite »."}


def compose(key, body):
    """A whole reply in our voice: greeting, the 🏠 line the know-how asks for, the text, closing and signature."""
    name, _, _, lang, gender, prop = PEOPLE[key]
    first, last = name.split()[0], name.split()[-1]
    greeting = GREET[lang][gender].format(first=first, last=last)
    return (f"{greeting}\n\n🏠 {PROPS[prop]['desc']} — {url(prop)}\n\n{body}\n\n{CLOSE[lang]}\n{SIGNATURE}")


def text(key, kind, extra="", **fields):
    lang = PEOPLE[key][3]
    return compose(key, BODY[kind][lang].format(extra=(" " + extra) if extra else "", **fields))


def proposal(key, day, start, end):
    return text(key, "proposal", day=mark(day, PEOPLE[key][3]), start=start, end=end)


def confirm(key, day, at, extra=""):
    return text(key, "confirm", extra, day=mark(day, PEOPLE[key][3]), time=at, address=PROPS[PEOPLE[key][5]]["address"])


def survey(key, day, at, public):
    name, _, _, lang, _, prop = PEOPLE[key]
    return compose(key, SURVEY[lang].format(public=public, desc=PROPS[prop]["desc"], ref=PROPS[prop]["ref"],
                                            address=PROPS[prop]["address"], day=mark(day, lang), time=at, name=name))


def ficha(trabalho, agregado, datas, disponibilidade, **optional):
    return clean_ficha({"trabalho": trabalho, "agregado": agregado, "datas": datas,
                        "disponibilidade": disponibilidade, **optional})


# ---------------------------------------------------------------------------------------------------------------
# The replies «Gerar respostas» writes in the demo, customer by customer: what a buyer reads first, so written by hand.

LUKAS = ("Sehr geehrter Herr Weber,\n\n🏠 {desc} — {url}\n\nvielen Dank für Ihre Nachricht. Die Wohnung ist noch "
         "verfügbar und ab Dezember bezugsfertig.\n\nDamit wir eine Besichtigung vorbereiten können, teilen Sie uns "
         "bitte mit:\n- Ihre berufliche Situation und Ihr monatliches Nettoeinkommen;\n- wie viele Personen in der "
         "Wohnung leben würden;\n- ab wann und für wie lange Sie mieten möchten;\n- an welchen Tagen und zu welchen "
         "Uhrzeiten Sie besichtigen könnten.\n\nMit freundlichen Grüßen,\n{sig}\n\nEnglish translation:\n\nDear Mr "
         "Weber,\n\nThank you for your message. The flat is still available and ready to move into from December.\n\n"
         "To arrange a viewing, could you tell us:\n- your professional situation and monthly net income;\n- how many "
         "people would live in the flat;\n- from when and for how long you would like to rent;\n- which days and "
         "times you could visit.\n\nKind regards,")


def demo_replies(today):
    visit_day = (today + timedelta(days=2)).isoformat()
    porto = (today + timedelta(days=1)).isoformat()
    return {
        "joao": {"reply_text": compose("joao", f"Lembramos que a sua visita ao apartamento está marcada para amanhã, "
                                       f"{mark(porto, 'pt')}, às 18:00, na {PROPS['P']['address']}. Se não puder "
                                       "comparecer, pedimos-lhe que nos avise por email.")},
        "chloe": {"reply_text": compose("chloe", f"This is a reminder that your viewing is booked for tomorrow, "
                                        f"{mark(porto, 'en')}, at 18:30, at {PROPS['P']['address']}. If you are unable "
                                        "to attend, please let us know by email.")},
        "priya": {"reply_text": confirm("priya", visit_day, "18:00", "And yes, the building has a lift."),
                  "visita": f"{visit_day} 18:00"},
        "catarina": {"reply_text": text("catarina", "first", "O prédio tem elevador. Não tem garagem, mas há "
                                        "estacionamento para residentes na rua, com dístico municipal. As visitas "
                                        "organizam-se por rondas: propomos-lhe dia e hora assim que tivermos a sua ficha.")},
        "lukas": {"reply_text": LUKAS.format(desc=PROPS["L"]["desc"], url=url("L"), sig=SIGNATURE),
                  "nota": "Respondido em alemão, com a tradução em inglês que a voz pede para outras línguas."},
        "carlos": {"reply_text": text("carlos", "second", "Con estos datos, su ficha queda completa."),
                   "ficha": {"trabalho": "Engenheiro numa empresa do setor automóvel, 2.800 € líquidos",
                             "agregado": "Casal", "datas": "A partir de 1 de novembro, mínimo de 1 ano",
                             "disponibilidade": "Ao fim da tarde"},
                   "nota": "Ficha completa: pode entrar na próxima ronda de visitas."},
        "miguel": {"reply_text": text("miguel", "first", "O apartamento fica a 5 minutos a pé do metro, a cerca de 15 "
                                      "minutos do Hospital de São João.")},
        "charlotte": {"reply_text": text("charlotte", "first", "There are two international schools within a 10-minute "
                                         "drive of the house.")},
        "olivia": {"reply_text": compose("olivia", "Yes, the house has central heating with a heat pump, and underfloor "
                                         "heating on the ground floor. There are two international schools within a "
                                         "10-minute drive. We are organising the next round of viewings and will try to "
                                         "fit in a Saturday morning, as you prefer; we will propose a time shortly."),
                   "nota": "Pede visita ao sábado de manhã: considera uma ronda ao sábado."},
        "nuno": {"reply_text": compose("nuno", "Obrigado pela sua mensagem. Estamos a organizar a próxima ronda de "
                                       "visitas à moradia e tomamos nota da sua preferência pelo sábado de manhã; "
                                       "voltamos ao seu contacto em breve com o dia e a hora.")}}


# ---------------------------------------------------------------------------------------------------------------
# The fake clock, Gmail and SMTP.

class Clock:
    """The backend's «now» while the history runs: a local date and time, moved by the script."""
    def __init__(self, today):
        self.today, self.moment = today, None

    def at(self, day, hhmm):
        hour, minute = map(int, hhmm.split(":"))
        self.moment = real_datetime.combine(self.today + timedelta(days=day), day_time(hour, minute)).astimezone()
        return self.moment

    def patches(self):
        clock = self

        class FakeDatetime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return clock.moment.astimezone(tz) if tz else clock.moment.astimezone().replace(tzinfo=None)

        class FakeDate(real_date):
            @classmethod
            def today(cls):
                return clock.moment.astimezone().date()

        fake_time = SimpleNamespace(**{name: getattr(real_time, name) for name in dir(real_time) if not name.startswith("_")})
        fake_time.time = lambda: clock.moment.timestamp()
        return [patch("backend.service.datetime", FakeDatetime), patch("backend.service.date", FakeDate),
                patch("backend.service.time", fake_time)]


class SMTP:
    def __init__(self, *args, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def login(self, *args): pass
    def send_message(self, msg): return {}


class Agency:
    """The fictitious agency's data folder, driven through the real service."""

    def __init__(self, folder, today):
        from .service import MailService
        self.folder, self.clock = Path(folder), Clock(today)
        self.inbox, self.counter = [], 0
        self.stack = ExitStack()
        for item in self.clock.patches():
            self.stack.enter_context(item)
        self.stack.enter_context(patch("backend.service.app_password", return_value="demo"))
        self.stack.enter_context(patch("backend.service.smtplib.SMTP_SSL", SMTP))
        self.stack.enter_context(patch("backend.service.read_messages", self.gmail))
        self.stack.enter_context(patch("backend.service.has_openai_api_key", return_value=True))
        self.stack.enter_context(patch("backend.service.openai_api_key", return_value="sk-demo"))
        self.stack.enter_context(patch("backend.api.openai_api_key", return_value="sk-demo"))
        self.clock.at(-14, "09:00")
        self.setup()
        self.svc = MailService(self.folder)

    def close(self):
        self.stack.close()

    def gmail(self, account, password, subject, date_from, date_to, mailbox="all", incoming_only=True,
              accept=None, outgoing=None, accept_outgoing=None, progress=None):
        found = [item for item in self.inbox if accept is None or accept(item)]
        self.inbox = []
        return found, len(found), "INBOX"

    # --- setup

    def setup(self):
        save_json(self.folder / "config.json", {**load_json(TEMPLATES / "config.example.json", {}), "account": ACCOUNT,
                                                "mailbox": "inbox", "openai_model": MODEL})
        voice = load_json(TEMPLATES / "voice.example.json", {})
        voice["style"]["signature"]["text"] = SIGNATURE
        voice["style"]["sender_name"].update(text=AGENCY, status="configured")
        voice["style"]["greeting"]["selected"] = "normal"
        voice["style"]["closing"]["selected"] = "formal"
        voice["style"]["languages"]["selected"] = "multilingual_en_backup"
        voice["style"]["digest_recipient"].update(text="gestao@casaexemplo.example", status="configured")
        voice["style"]["visits_closed"].update(status="configured", text=(
            "Agradecemos o seu interesse neste imóvel. Informamos que as visitas terminaram e que o imóvel já não está "
            "disponível. Guardamos o seu contacto e teremos todo o gosto em avisá-lo de novas oportunidades."))
        voice["style"]["consent_request"].update(status="configured", text=(
            "Podemos guardar o seu contacto para lhe enviarmos outros imóveis que correspondam ao que procura? Basta "
            "responder «sim» a este email; pode pedir-nos a qualquer momento que o apaguemos."))
        voice["application_instructions"] = ("Tom profissional e cordial, sem exclamações nem frases feitas. Responde só "
                                             "ao que o cliente perguntou e ao que falta saber para a visita.")
        save_json(self.folder / "voice.json", voice)
        for prop in PROPS.values():
            profile = load_json(TEMPLATES / "profile.example.json", {})
            example = profile["property"]
            general = profile["reply"]["prompts"]["general"]
            general["text"] = general["text"].replace(example["reference"], prop["ref"]).replace(example["description"], prop["desc"])
            profile["account"] = ACCOUNT
            profile["property"].update(reference=prop["ref"], description=prop["desc"], advertised_rent_eur=prop["rent"],
                                       listing_id=prop["listing"], listing_url=f"https://anuncios.example/imovel/{prop['listing']}/",
                                       advertiser=AGENCY, information_source="Demonstração com dados fictícios.")
            profile["match"].update(subject_property_reference_equals=prop["ref"],
                                    if_body_listing_id_present_must_equal=prop["listing"])
            profile["reply"]["never_reply_to"] = ["reply@idealista.pt", ACCOUNT]
            save_json(self.folder / "properties" / prop["ref"] / "profile.json", profile)
            knowledge = self.folder / "properties" / prop["ref"] / "knowledge"
            knowledge.mkdir(parents=True, exist_ok=True)
            (knowledge / "anuncio.md").write_text(f"# {prop['desc']}\n\nRenda: {prop['rent']} € por mês.\nMorada: "
                                                  f"{prop['address']}\n\n" + "\n".join(f"- {fact}" for fact in prop["facts"]) + "\n")
        (self.folder / "knowledge").mkdir(exist_ok=True)
        (self.folder / "knowledge" / "know-how.md").write_text(
            "# Know-how da agência\n\n## Lembrete do imóvel, logo após a saudação\nEm todas as respostas, logo a seguir "
            "à saudação, uma linha: «🏠 título do anúncio — link do anúncio». Nunca inventes nem uses o de outro imóvel.\n\n"
            "## Visitas\nArrendamentos só depois de uma visita presencial. As visitas organizam-se por rondas: propomos um "
            "dia e um intervalo de horas e cada cliente escolhe a hora. Ao confirmar, indica sempre a hora e a morada.\n\n"
            "## Documentos\nPara avançar: recibos de vencimento dos últimos 3 meses e IRS do ano anterior; com fiador "
            "quando o rendimento for inferior a três rendas.\n")
        (self.folder / "logs").mkdir(exist_ok=True)

    # --- the owner's and the customers' actions

    def lead(self, key, message, hhmm="10:00"):
        name, email, phone, _, _, prop = PEOPLE[key]
        info = PROPS[prop]
        self.counter += 1
        uid = f"demo{self.counter:03d}"
        self.inbox.append({"uid": uid, "gmail_message_id": uid, "thread_id": f"t{uid}", "date": self.clock.moment.isoformat(),
                           "from": [{"name": "idealista", "email": "reply@idealista.pt"}], "to": [{"name": "", "email": ACCOUNT}],
                           "cc": [], "reply_to": [{"name": "", "email": email}],
                           "subject": f"Nova mensagem de {name} sobre o teu imóvel, com ref: {info['ref']} | {AGENCY}",
                           "message_id": f"<{uid}@portal.example>", "in_reply_to": "", "references": "",
                           "body_text": "\n".join(["Tens uma nova mensagem que aguarda resposta", name, phone, email, message,
                                                   f"Ref. {info['ref']} | {AGENCY}", f"Código do anúncio: {info['listing']}"]),
                           "body_truncated": False})

    def says(self, key, message):
        name, email, _, _, _, prop = PEOPLE[key]
        conversation = self.svc.load(PROPS[prop]["ref"])["conversations"][email]
        sent = conversation["sent_message_ids"]
        self.counter += 1
        uid = f"demo{self.counter:03d}"
        self.inbox.append({"uid": uid, "gmail_message_id": uid, "thread_id": conversation["thread_ids"][-1],
                           "date": self.clock.moment.isoformat(), "from": [{"name": name, "email": email}],
                           "to": [{"name": AGENCY, "email": ACCOUNT}], "cc": [], "reply_to": [],
                           "subject": "Re: " + re.sub(r"^(?:Re:\s*)+", "", conversation.get("subject") or PROPS[prop]["desc"]),
                           "message_id": f"<{uid}@mail.example>", "in_reply_to": sent[-1], "references": " ".join(sent),
                           "body_text": message, "body_truncated": False})

    def read(self):
        """A read; the automatic reminders it prepares are taken off (the script has the customers answer), except
        today's visit reminders, which the demo shows."""
        result = self.svc.read()
        today = self.clock.moment.astimezone().date() == self.clock.today
        kinds = {"reminder"} if today else {"reminder", "visit_reminder"}
        for queue in self.svc.pending()["properties"]:
            ids = [item["id"] for item in queue["emails"] if item.get("kind") in kinds]
            if ids:
                self.svc.dismiss(ids, queue["revision"], queue["property_ref"])
        return result

    def queue(self, prop):
        return next(q for q in self.svc.pending()["properties"] if q["property_ref"] == PROPS[prop]["ref"])

    def item(self, key, kind=None):
        email = PEOPLE[key][1]
        return next(item for item in self.queue(PEOPLE[key][5])["emails"]
                    if (item.get("recipient") or {}).get("email", "").casefold() == email and (kind is None or item.get("kind") == kind))

    def answer(self, prop, replies):
        """«Gerar respostas» and «Enviar» for these customers: [(key, text, {"slot"?, "ficha"?, "kind"?})]."""
        ref = PROPS[prop]["ref"]
        drafts, visits, fichas = [], [], []
        for key, reply, *more in replies:
            extra = more[0] if more else {}
            item = self.item(key, extra.get("kind"))
            drafts.append({"id": item["id"], "reply_text": reply})
            if extra.get("slot"):
                visits.append({"id": item["id"], "visit_slot": extra["slot"]})
            if extra.get("ficha"):
                fichas.append({"id": item["id"], "ficha": extra["ficha"]})
        self.svc.drafts(drafts, self.queue(prop)["revision"], ref, visits, fichas)
        prompt_tokens, completion_tokens = 2400 + 950 * len(drafts), 290 * len(drafts)
        from .openai_client import estimate_cost_usd
        self.svc.log("openai_usage", model=MODEL, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                     total_tokens=prompt_tokens + completion_tokens, reference=ref,
                     cost_usd=round(estimate_cost_usd(MODEL, prompt_tokens, completion_tokens), 6))
        preview = self.svc.preview([draft["id"] for draft in drafts], ref)
        self.clock.moment += timedelta(minutes=12)
        return self.svc.send(preview["preview_token"], True, ref)

    def round(self, prop, day, start, end, keys):
        self.svc.propose_visits(PROPS[prop]["ref"], day.isoformat(), start, end, [PEOPLE[key][1] for key in keys])
        return self.answer(prop, [(key, proposal(key, day.isoformat(), start, end), {"kind": "visit_proposal"}) for key in keys])


# ---------------------------------------------------------------------------------------------------------------
# Two weeks of the agency, day by day (0 is the day the demo is built; the demo moves it to the viewer's day).

def history(agency):
    a, at, today = agency, agency.clock.at, agency.clock.today
    day = lambda offset: today + timedelta(days=offset)
    for prop, info in PROPS.items():
        a.svc.fill_fuel(info["ref"], 10)
        a.svc.save_panel(info["ref"], 24, info["km"], 6.5)

    at(-13, "09:10"); a.lead("mariana", "Bom dia, vi o anúncio do T2 em Campo de Ourique. Ainda está disponível? Somos um casal sem filhos e gostaríamos de visitar.")
    at(-13, "10:40"); a.lead("sophie", "Bonjour, je suis intéressée par l'appartement à Campo de Ourique. Est-il toujours disponible ? Je travaille à Lisbonne depuis un an.")
    at(-13, "18:00"); a.read()
    at(-13, "18:20"); a.answer("L", [("mariana", text("mariana", "first")), ("sophie", text("sophie", "first"))])

    at(-12, "08:30"); a.says("mariana", "Bom dia. Trabalho como enfermeira no Hospital de Santa Maria e o meu marido é engenheiro de software; temos um rendimento conjunto de cerca de 4.200 € líquidos. Queríamos entrar a 1 de novembro, por dois anos ou mais. Durante a semana ao fim da tarde, ou sábado de manhã.")
    at(-12, "11:15"); a.lead("tiago", "Olá. O apartamento tem estacionamento? Tenho um cão pequeno, é problema?")
    at(-12, "12:00"); a.lead("joao", "Boa tarde, gostava de saber se o T1 no Bonfim ainda está disponível e se inclui móveis.")
    at(-12, "18:30"); a.read()
    at(-12, "18:45")
    a.answer("L", [("mariana", text("mariana", "second"), {"ficha": ficha("Enfermeira e engenheiro de software, ~4.200 € líquidos", "Casal, sem filhos", "A partir de 1 de novembro, 2 anos ou mais", "Fim de tarde durante a semana; sábado de manhã")}),
                   ("tiago", text("tiago", "first", "O prédio não tem garagem, mas há estacionamento para residentes na rua. Animais de pequeno porte são bem-vindos."))])
    a.answer("P", [("joao", text("joao", "first", "O apartamento é entregue mobilado e equipado."))])

    at(-11, "09:00"); a.says("sophie", "Merci. Je suis architecte dans un cabinet à Lisbonne (CDI), revenu net 3 100 €. J'habiterais seule. Je souhaiterais emménager début novembre, pour au moins un an. Disponible en semaine après 17h.")
    at(-11, "10:20"); a.lead("chloe", "Hi! I'm a postdoc researcher starting at the University of Porto in November. Is the flat still available?")
    at(-11, "15:00"); a.lead("olivia", "Hello, we're relocating from London with our two children. Is the house in Estoril still available from December? We also have a dog.")
    at(-11, "18:10"); a.read()
    at(-11, "18:30")
    a.answer("L", [("sophie", text("sophie", "second"), {"ficha": ficha("Arquiteta num gabinete em Lisboa, contrato sem termo, 3.100 € líquidos", "Sozinha", "Início de novembro, pelo menos 1 ano", "Dias úteis depois das 17h")})])
    a.answer("P", [("chloe", text("chloe", "first"))])
    a.answer("C", [("olivia", text("olivia", "first", "The house has a private garden of around 300 m² and pets are welcome."))])

    at(-10, "09:30"); a.says("tiago", "Trabalho numa agência de publicidade, 2.300 € líquidos. Vivo sozinho com o meu cão, um beagle. Precisava de casa em novembro. Posso visitar à hora de almoço.")
    at(-10, "11:00"); a.says("joao", "Sou professor numa escola secundária no Porto, 1.650 € líquidos. Vivo sozinho. Gostaria de entrar em meados de outubro, por tempo indeterminado. Disponível depois das 18h.")
    at(-10, "14:00"); a.lead("emma", "Hi, is the apartment available for a short stay of three months?")
    at(-10, "18:00"); a.read()
    at(-10, "18:20")
    a.answer("L", [("tiago", text("tiago", "second"), {"ficha": ficha("Agência de publicidade, 2.300 € líquidos", "Sozinho, com um cão", "Novembro", "Hora de almoço", animais="Um beagle")}),
                   ("emma", compose("emma", "Thank you for your interest. The minimum lease for this property is one year, so unfortunately a three-month stay would not be possible."))])
    a.answer("P", [("joao", text("joao", "second"), {"ficha": ficha("Professor do ensino secundário, 1.650 € líquidos", "Sozinho", "Meados de outubro, sem prazo", "Depois das 18h")})])

    at(-9, "10:00"); a.lead("carlos", "Hola, ¿sigue disponible el piso en Bonfim? Me mudo a Oporto por trabajo.")
    at(-9, "12:30"); a.says("olivia", "Thanks! My husband and I both work remotely for a UK fintech, combined net income around 10,000 € a month. Family of four plus a golden retriever. We'd like to move in on 1 December, for two years or more. Weekdays at any time.")
    at(-9, "16:00"); a.says("chloe", "I'll be a postdoc at the University on a three-year contract, net 2,100 € a month. Just me. From 1 November, ideally for three years. Free on weekday evenings.")
    at(-9, "18:40"); a.read()
    at(-9, "19:00")
    a.answer("P", [("carlos", text("carlos", "first")),
                   ("chloe", text("chloe", "second"), {"ficha": ficha("Investigadora pós-doc na Universidade do Porto, 2.100 € líquidos", "Sozinha", "A partir de 1 de novembro, 3 anos", "Dias úteis ao fim da tarde")})])
    a.answer("C", [("olivia", text("olivia", "second"), {"ficha": ficha("Casal em trabalho remoto numa fintech do Reino Unido, ~10.000 € líquidos", "Casal com dois filhos", "1 de dezembro, 2 anos ou mais", "Dias úteis, a qualquer hora", animais="Um golden retriever")})])

    at(-8, "09:15"); a.says("emma", "Thanks for the reply. Then it's not for me, I'm no longer interested.")
    at(-8, "11:00"); a.lead("nuno", "Boa tarde. A moradia está disponível? Qual o valor da caução?")
    at(-8, "18:00"); a.read()
    a.svc.set_ignored(PROPS["L"]["ref"], PEOPLE["emma"][1], True, "Cliente disse que não tem interesse.", "grey")
    at(-8, "18:15"); a.answer("C", [("nuno", text("nuno", "first", "A caução corresponde a duas rendas."))])

    at(-7, "10:00"); a.lead("rafael", "Olá! Tudo bem? Tenho interesse no apartamento em Campo de Ourique. Ainda está disponível?")
    at(-7, "13:00"); a.lead("beatriz", "Olá, o apartamento aceita estudantes?")
    at(-7, "18:15"); a.read()
    at(-7, "18:30")
    a.answer("L", [("rafael", text("rafael", "first"))])
    a.answer("P", [("beatriz", text("beatriz", "first", "Aceitamos estudantes, com fiador."))])

    at(-6, "08:40"); a.says("rafael", "Sou designer de UX numa empresa de tecnologia, 3.400 € líquidos. Moro com a minha esposa. Queremos mudar em dezembro, por dois anos. Disponível ao fim da tarde.")
    at(-6, "09:30"); a.read()
    at(-6, "09:45"); a.answer("L", [("rafael", text("rafael", "second"), {"ficha": ficha("Designer de UX numa empresa de tecnologia, 3.400 € líquidos", "Casal", "Dezembro, 2 anos", "Fim da tarde")})])
    at(-6, "10:00"); a.round("L", day(-3), "10:00", "13:00", ["mariana", "sophie", "tiago"])

    at(-5, "09:00"); a.says("mariana", "Perfeito, pode ser às 10:00?")
    at(-5, "11:00"); a.says("sophie", "Oui, 10h30 me convient très bien.")
    at(-5, "13:00"); a.says("tiago", "Pode ser às 11:30, à hora de almoço.")
    at(-5, "14:00"); a.lead("priya", "Hello, I'm moving to Lisbon for a job at a tech company. Is the T2 still available? Could I visit next week?")
    at(-5, "18:00"); a.read()
    at(-5, "18:20")
    visit = day(-3).isoformat()
    a.answer("L", [("mariana", confirm("mariana", visit, "10:00"), {"slot": f"{visit} 10:00"}),
                   ("sophie", confirm("sophie", visit, "10:30"), {"slot": f"{visit} 10:30"}),
                   ("tiago", confirm("tiago", visit, "11:30"), {"slot": f"{visit} 11:30"}),
                   ("priya", text("priya", "first", "Viewings are organised in weekly rounds; we will propose a day and time as soon as the next round is set."))])

    at(-4, "11:00"); a.says("nuno", "Obrigado. Somos um casal com uma filha de 6 anos; eu sou gestor bancário e a minha mulher é médica, cerca de 6.000 € líquidos. Queríamos entrar em janeiro. Disponível ao sábado.")
    at(-4, "15:00"); a.says("priya", "I'm a data scientist on a permanent contract, net 3,800 € a month. Living alone. Start on 15 November, for at least two years. Weekday evenings work best.")
    at(-4, "18:20"); a.read()
    at(-4, "18:40")
    a.answer("C", [("nuno", text("nuno", "second"), {"ficha": ficha("Gestor bancário e médica, ~6.000 € líquidos", "Casal com uma filha de 6 anos", "Janeiro", "Sábados")})])
    a.answer("L", [("priya", text("priya", "second"), {"ficha": ficha("Cientista de dados, contrato sem termo, 3.800 € líquidos", "Sozinha", "15 de novembro, pelo menos 2 anos", "Dias úteis ao fim da tarde")})])
    at(-4, "19:00"); a.round("P", day(1), "18:00", "19:30", ["joao", "chloe"])

    at(-3, "13:30")
    ref = PROPS["L"]["ref"]
    a.svc.check_visit(ref, PEOPLE["mariana"][1], True, "Muito boa impressão: pontuais e organizados.", "Foi um gosto mostrar-lhe o apartamento.")
    a.svc.check_visit(ref, PEOPLE["sophie"][1], True, "Gostou muito da varanda; ainda compara com outro imóvel.", "Obrigado pelas suas perguntas sobre o bairro.")
    a.svc.check_visit(ref, PEOPLE["tiago"][1], False, "Não apareceu nem avisou.", "")
    a.svc.visit_thanks(ref, PEOPLE["mariana"][1])
    a.svc.visit_thanks(ref, PEOPLE["sophie"][1])
    at(-3, "14:00")
    a.answer("L", [("mariana", survey("mariana", visit, "10:00", "Foi um gosto mostrar-lhe o apartamento."), {"kind": "visit_thanks"}),
                   ("sophie", survey("sophie", visit, "10:30", "Merci pour vos questions sur le quartier."), {"kind": "visit_thanks"}),
                   ("tiago", compose("tiago", f"Tínhamos a sua visita marcada para {mark(visit, 'pt')}, às 11:30, mas não nos foi possível encontrarmo-nos. Se quiser dizer-nos alguma coisa, pode responder a este email; ficamos a aguardar caso haja uma nova ronda de visitas."), {"kind": "visit_missed"})])
    at(-3, "16:00"); a.says("joao", "18:00 está ótimo, obrigado.")
    at(-3, "17:00"); a.says("chloe", "18:30 works perfectly for me.")
    at(-3, "18:00"); a.read()
    at(-3, "18:15")
    porto = day(1).isoformat()
    a.answer("P", [("joao", confirm("joao", porto, "18:00"), {"slot": f"{porto} 18:00"}),
                   ("chloe", confirm("chloe", porto, "18:30"), {"slot": f"{porto} 18:30"})])

    at(-2, "09:00"); a.says("mariana", "1. O imóvel: 5\n2. O consultor que o recebeu na visita: 5\n3. A marcação da visita e a troca de emails: 5\n4. Continua interessado em arrendar este imóvel? sim\n5. Comentário: Adorámos a luz e a varanda. Podemos avançar com os documentos.\n\nConfirmo a visita.\n\nObrigada,\nMariana")
    at(-2, "12:00"); a.says("sophie", "1. Le logement : 4\n2. Le conseiller qui vous a reçu : 5\n3. La prise de rendez-vous et les échanges d'emails : 4\n4. Êtes-vous toujours intéressée par ce logement ? peut-être\n5. Commentaire : Très bel appartement, un peu bruyant côté rue.\n\nJe confirme la visite.\n\nCordialement,\nSophie")
    at(-2, "13:00"); a.says("tiago", "Peço desculpa, tive um imprevisto no trabalho. Ainda é possível visitar noutro dia?")
    at(-2, "18:00"); a.read()
    at(-2, "18:20")
    a.answer("L", [("mariana", compose("mariana", "Muito obrigado pelas suas respostas e pelas palavras simpáticas. Ficamos muito contentes por ter gostado do apartamento; enviamos-lhe em breve a lista de documentos para avançarmos.")),
                   ("sophie", compose("sophie", "Merci beaucoup pour vos réponses. Nous prenons note de votre remarque sur le bruit côté rue : les fenêtres sont équipées d'un double vitrage récent. N'hésitez pas à nous écrire si vous avez d'autres questions.")),
                   ("tiago", compose("tiago", "Com certeza. Ficamos com o seu contacto e incluímo-lo na próxima ronda de visitas, que vamos propor em breve."))])
    a.svc.set_selection(ref, PEOPLE["mariana"][1], "chosen")
    a.svc.set_selection(ref, PEOPLE["sophie"][1], "suplente")
    a.svc.set_selection(ref, PEOPLE["rafael"][1], "shortlist")
    a.svc.request_documents(ref, PEOPLE["mariana"][1])
    at(-2, "18:40")
    a.answer("L", [("mariana", compose("mariana", "Para avançarmos com o arrendamento, pedimos-lhe que nos envie, em resposta a este email:\n- os recibos de vencimento dos últimos 3 meses (de ambos);\n- a declaração de IRS do ano anterior.\nAssim que os recebermos, preparamos a minuta do contrato."), {"kind": "docs_request"})])

    at(-1, "10:00"); a.round("L", day(2), "17:00", "19:00", ["rafael", "priya", "tiago"])
    at(-1, "12:30"); a.svc.set_document(ref, PEOPLE["mariana"][1], "candidato:recibos", True)
    at(-1, "16:00"); a.says("rafael", "Pode ser às 17:30.")
    at(-1, "18:00"); a.read()
    at(-1, "18:15")
    second = day(2).isoformat()
    a.answer("L", [("rafael", confirm("rafael", second, "17:30"), {"slot": f"{second} 17:30"})])

    # This morning: three emails already in the queue when the demo opens.
    at(0, "08:10"); a.says("priya", "Great, 18:00 works for me. Is there a lift in the building?")
    at(0, "08:45"); a.says("carlos", "Gracias. Soy ingeniero en una empresa de automoción, 2.800 € netos. Vivo con mi pareja. Nos gustaría entrar el 1 de noviembre, por un año como mínimo. Disponible por las tardes.")
    at(0, "09:05"); a.says("olivia", "Could you tell us whether the house has central heating, and whether a viewing on a Saturday morning would be possible? Also, is there a good international school nearby?")
    at(0, "09:30"); a.read()


def new_mail(agency):
    """What «Ler emails» brings in the demo: new leads and a customer's answer."""
    a, at = agency, agency.clock.at
    at(0, "10:35"); a.lead("catarina", "Bom dia. Somos um casal com um bebé de 8 meses. O prédio tem elevador e é possível ter lugar de garagem? Gostaríamos de visitar esta semana.")
    at(0, "10:50"); a.lead("lukas", "Guten Tag, ich interessiere mich für die Wohnung in Campo de Ourique. Ich arbeite ab Dezember in Lissabon. Ist die Wohnung noch frei?")
    at(0, "11:02"); a.lead("miguel", "Boa tarde, o T1 ainda está disponível? Sou enfermeiro no Hospital de São João.")
    at(0, "11:10"); a.lead("charlotte", "Good morning, we are a family of three moving from Amsterdam in January. Is the villa available, and is there a school nearby?")
    at(0, "11:18"); a.says("nuno", "Bom dia. Sábado de manhã seria possível visitar a moradia?")
    at(0, "11:30")


# ---------------------------------------------------------------------------------------------------------------
# Recording: what the API answers at each stage of the demo.

def fake_complete(agency, replies):
    """The OpenAI API of the demo: the hand-written replies above, as the reply prompt asks for them."""
    def complete(key, model, prompt, timeout=90, json_mode=True):
        if not json_mode:
            return ("Os clientes ativos preferem sobretudo o fim da tarde nos dias úteis; dois referem também o sábado de "
                    "manhã. Quem parece mais interessado já tem a ficha completa e datas de entrada entre novembro e "
                    "dezembro. Um intervalo das 17:00 às 19:00 num dia útil serviria a maioria."), \
                {"prompt_tokens": 1800, "completion_tokens": 120, "total_tokens": 1920}
        by_short = {short_id(email["id"]): email for queue in agency.svc.pending()["properties"] for email in queue["emails"]}
        people = {info[1]: person for person, info in PEOPLE.items()}
        answers = []
        for found in re.findall(r"--- id: (\S+) \|", prompt):
            email = by_short.get(found)
            person = people.get(((email or {}).get("recipient") or {}).get("email", "").casefold())
            if person in replies:
                answers.append({"id": found, **replies[person]})
        count = max(1, len(answers))
        usage = {"prompt_tokens": 2400 + 950 * count, "completion_tokens": 290 * count}
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
        return json.dumps({"respostas": answers}, ensure_ascii=False), usage
    return complete


def key_of(path, body=None):
    return path + ("" if body is None else "|" + json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def test_client(folder):
    """The page's own app, called in-process (Starlette's test client), without its notice about httpx."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from starlette.testclient import TestClient
    from .api import web_app
    return TestClient(web_app(folder, TOKEN), base_url="http://127.0.0.1:8765")


class Recorder:
    def __init__(self, agency):
        self.agency = agency
        self.client = test_client(agency.folder)

    def call(self, path, body=None):
        headers = {"X-Bot-Mail-Token": TOKEN}
        response = (self.client.get("/" + path, headers=headers) if body is None
                    else self.client.post("/" + path, json=body, headers=headers))
        data = response.json()
        if response.status_code != 200:
            raise RuntimeError(f"{path}: {data.get('error')}")
        return data

    def snapshot(self):
        """Every call the page makes to show what is there, with the bodies it sends."""
        refs = [info["ref"] for info in PROPS.values()]
        found = {}
        for path in ("api/state", "api/settings", "api/digest", "api/todo", "api/contacts"):
            found[key_of(path)] = self.call(path)
        for days in (3, 7, 14, 30, 90):
            found[key_of("api/metrics", {"days": days})] = self.call("api/metrics", {"days": days})
        for ref in refs:
            body = {"property_ref": ref}
            for path in ("api/knowledge", "api/visits/candidates", "api/visits/round-summary", "api/visits/round",
                         "api/contacts/ignored",
                         "api/visits/analysis-prompt"):
                found[key_of(path, body)] = self.call(path, body)
        found[key_of("api/knowledge", {"property_ref": None})] = self.call("api/knowledge", {"property_ref": None})
        return found


def record(agency):
    """The demo's recordings: the stages (0 as it opens, 1 after «Ler emails», 2 after «Gerar respostas», 3 after
    «Enviar»), the per-email results of each step, and the other actions' answers, recorded on copies."""
    replies = demo_replies(agency.clock.today)
    agency.stack.enter_context(patch("backend.api.complete", fake_complete(agency, replies)))
    agency.stack.enter_context(patch("backend.service.complete", fake_complete(agency, replies)))
    rec = Recorder(agency)
    stages = [rec.snapshot()]
    new_mail(agency)
    read = rec.call("api/read", {"days": 7})
    stages.append(rec.snapshot())
    side = Path(tempfile.mkdtemp(prefix="webdemo-side-"))
    shutil.copytree(agency.folder, side / "data")

    generated, notes, prompts, fuel, preview_of, active_of = {}, {}, {}, {}, {}, {}
    for queue in read["properties"]:
        ref, ids = queue["property_ref"], [email["id"] for email in queue["emails"] if not email.get("blocked")]
        if not ids:
            continue
        result = rec.call("api/prompt/generate", {"property_ref": ref, "ids": ids, "extra": ""})
        by_id = {short_id(email["id"]): email["id"] for email in queue["emails"]}
        for email in next(q for q in result["state"]["properties"] if q["property_ref"] == ref)["emails"]:
            if email["id"] in ids:
                generated[email["id"]] = email
        for note in result["notes"]:
            notes[by_id.get(note.get("id"), note.get("id"))] = note
        prompts[ref], fuel[ref] = result["prompts"], result["fuel"]
    stages.append(rec.snapshot())
    for queue in read["properties"]:
        ref = queue["property_ref"]
        ids = [email_id for email_id in generated if any(e["id"] == email_id for e in queue["emails"])]
        if not ids:
            continue
        preview = rec.call("api/preview", {"property_ref": ref, "ids": ids})
        for reply in preview["replies"]:
            preview_of[reply["id"]] = {key: reply[key] for key in ("to", "subject", "warnings")}
        rec.call("api/send", {"property_ref": ref, "preview_token": preview["preview_token"], "confirmed": True})
    state = rec.call("api/state")
    for queue in read["properties"]:
        active = {item["email"]: item for q in state["properties"] if q["property_ref"] == queue["property_ref"]
                  for item in q.get("active") or []}
        for email in queue["emails"]:
            address = ((email.get("recipient") or {}).get("email") or "").casefold()
            if address in active:
                active_of[email["id"]] = active[address]
    stages.append(rec.snapshot())
    csv = agency.svc.contacts_csv()

    # The other actions, each on a fresh copy of stage 1 (what the viewer sees after «Ler emails»).
    actions = record_actions(side / "data", stages[1])
    shutil.rmtree(side, ignore_errors=True)
    return {"stages": stages, "read": {"added": read.get("added", 0)}, "generated": generated, "notes": notes,
            "prompts": prompts, "fuel": fuel, "previews": preview_of, "active": active_of, "actions": actions}, csv


def record_actions(base, stage):
    found = {}
    state = stage[key_of("api/state")]
    lisboa = PROPS["L"]["ref"]

    def attempt(path, body, per=None):
        copy = Path(tempfile.mkdtemp(prefix="webdemo-act-")) / "data"
        shutil.copytree(base, copy)
        client = test_client(copy)
        response = client.post("/" + path, json=body, headers={"X-Bot-Mail-Token": TOKEN})
        shutil.rmtree(copy.parent, ignore_errors=True)
        if response.status_code == 200:
            answer = response.json()
            if "state" in answer:  # only what the action added to the queue: demo-api.js keeps the rest
                before = {e["id"] for q in state["properties"] for e in q["emails"]}
                answer["new_emails"] = {q["property_ref"]: [e for e in q["emails"] if e["id"] not in before]
                                        for q in answer.pop("state")["properties"]}
            answer.pop("settings", None)
            found[path + ("|" + per if per else "")] = answer

    for queue in state["properties"]:
        for active in queue.get("active") or []:
            attempt("api/active/write", {"property_ref": queue["property_ref"], "email": active["email"]}, active["email"])
    for key in ("mariana", "sophie"):
        attempt("api/visits/thanks", {"property_ref": lisboa, "email": PEOPLE[key][1]}, PEOPLE[key][1])
    attempt("api/visits/analyze", {"property_ref": lisboa})
    attempt("api/knowledge/note", {"property_ref": lisboa, "scope": "property", "text": "Exemplo de nota."})
    attempt("api/digest/refresh", {})
    attempt("api/fuel/fill", {"property_ref": lisboa, "capacity_eur": 10})
    return found


# ---------------------------------------------------------------------------------------------------------------
# Writing the static folder.

def pack(data):
    """The recordings with each distinct answer written once (several stages answer the same)."""
    blobs, index = [], {}

    def ref(value):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if text not in index:
            index[text] = len(blobs)
            blobs.append(value)
        return index[text]
    data = dict(data)
    data["stages"] = [{key: ref(value) for key, value in stage.items()} for stage in data["stages"]]
    data["blobs"] = blobs
    return data


def write_site(destination, data, csv, build_day):
    from .api import DISPLAY_VERSION
    destination = Path(destination)
    if destination.exists():
        raise ValueError("O destino já existe; escolhe uma pasta nova para a demonstração.")
    destination.mkdir(parents=True)
    shutil.copy2(FRONTEND / "app.js", destination / "app.js")
    shutil.copy2(FRONTEND / "style.css", destination / "style.css")
    shutil.copytree(FRONTEND / "themes", destination / "themes")
    shutil.copytree(FRONTEND / "sounds", destination / "sounds")
    shutil.copytree(FRONTEND / "brand", destination / "brand")
    shutil.copy2(SHIM / "demo-api.js", destination / "demo-api.js")
    shutil.copy2(SHIM / "demo.css", destination / "demo.css")
    page = (FRONTEND / "index.html").read_text(encoding="utf-8")
    page = (page.replace(' nonce="{{NONCE}}"', "").replace("{{TOKEN}}", TOKEN)
            .replace("{{VERSION}}", DISPLAY_VERSION + " · demo").replace("{{BUILD_AT}}", "Demonstração · dados fictícios"))
    page = page.replace('<script src="app.js"></script>',
                        '<script src="demo-data.js"></script>\n<script src="demo-api.js"></script>\n<script src="app.js"></script>')
    page = page.replace("</head>", '<link rel="stylesheet" href="demo.css">\n</head>', 1)
    if "demo-api.js" not in page or "{{" in page:
        raise RuntimeError("index.html mudou: o gerador da demonstração tem de ser revisto.")
    (destination / "index.html").write_text(page, encoding="utf-8")
    payload = json.dumps({**pack(data), "build_day": build_day.isoformat(), "account": ACCOUNT},
                         ensure_ascii=False, separators=(",", ":"))
    (destination / "demo-data.js").write_text("window.DEMO_DATA = " + payload + ";\n", encoding="utf-8")
    (destination / "contactos.csv").write_bytes(csv if isinstance(csv, bytes) else csv.encode("utf-8"))
    (destination / "LEIA-ME.txt").write_text(
        "ARIA, by BigLearn.pt — versão de demonstração\n\n"
        "Pasta estática: envia todo o conteúdo para qualquer servidor HTTP (ou abre index.html no browser).\n"
        "Dados fictícios e respostas gravadas: não lê nem envia emails e não chama nenhuma IA.\n"
        "As datas acompanham o dia de quem vê a demonstração.\n", encoding="utf-8")
    archive = destination.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for file in sorted(destination.rglob("*")):
            if file.is_file():
                bundle.write(file, file.relative_to(destination))
    return destination, archive


def build(destination, today=None):
    """Simulates the agency in a temporary folder, records the demo and writes the static site (and its .zip)."""
    today = today or real_date.today()
    work = Path(tempfile.mkdtemp(prefix="webdemo-"))
    agency = Agency(work / "data", today)
    try:
        history(agency)
        data, csv = record(agency)
    finally:
        agency.close()
        shutil.rmtree(work, ignore_errors=True)
    return write_site(destination, data, csv, today)
