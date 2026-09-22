import json
from pathlib import Path
from unittest.mock import patch
import pytest
from backend.service import MailService
from backend.store import add_contacts, load_contacts, save_contacts, save_json

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "backend" / "templates"
REF = "REF_IMOVEL"
IDEALISTA = {"name": "idealista", "email": "reply@idealista.pt"}
CUSTOMER = "ana.exemplo@example.com"


@pytest.fixture
def service(tmp_path):
    save_json(tmp_path / "config.json", {"account": "owner@example.com", "lookback_days": 2})
    profile = json.loads((TEMPLATES / "profile.example.json").read_text(encoding="utf-8"))
    save_json(tmp_path / "properties" / REF / "profile.json", profile)
    voice = json.loads((TEMPLATES / "voice.example.json").read_text(encoding="utf-8"))
    for key, choice in (("greeting", "formal"), ("languages", "pt_en_fr"), ("closing", "cordial")):
        voice["style"][key]["selected"] = choice
    save_json(tmp_path / "voice.json", voice)
    return MailService(tmp_path)


def lead(key, reply_to=(CUSTOMER,), ref=REF, listing="00000000", body_email=CUSTOMER, sender=IDEALISTA):
    """A portal notice as read_messages returns it (fictitious customer)."""
    body = "\n".join(["Tens uma nova mensagem que aguarda resposta", "Ana Exemplo", "900 000 001", body_email,
                      "Bom dia, gostaria de visitar o imóvel.", f"Ref. {ref} | Anunciante",
                      f"Código do anúncio: {listing}", "1.000 €"])
    return {"gmail_message_id": key, "thread_id": f"t{key}", "message_id": f"<{key}@portal.example>",
            "from": [sender], "reply_to": [{"name": "", "email": address} for address in reply_to],
            "subject": f"🤩 Nova mensagem (com perfil) de Ana Exemplo sobre o teu imóvel, com ref: {ref} | Anunciante",
            "body_text": body, "body_truncated": False}


def read(service, messages):
    with patch("backend.service.app_password", return_value="fake"), patch(
            "backend.service.read_messages", return_value=(messages, len(messages), "INBOX")):
        return service.read()


def test_read_registers_a_new_contact_awaiting_rgpd(service):
    read(service, [lead("1")])
    [row] = load_contacts(service.folder).values()
    assert row == {"email": CUSTOMER, "nome": "Ana Exemplo", "telefone": "900 000 001",
                   "primeiro_contacto": row["primeiro_contacto"], "imovel": REF, "fonte": "Idealista",
                   "rgpd": "por_pedir", "rgpd_data": "", "rgpd_prova": ""}
    assert (service.folder / "contactos.csv").stat().st_mode & 0o077 == 0


def test_second_lead_from_same_customer_keeps_first_date_and_rgpd(service):
    read(service, [lead("1")])
    first_day = load_contacts(service.folder)[(CUSTOMER, REF)]["primeiro_contacto"]
    contacts = load_contacts(service.folder)
    contacts[(CUSTOMER, REF)]["rgpd"] = "sim"
    save_contacts(service.folder, contacts)

    read(service, [lead("2")])
    contacts = load_contacts(service.folder)
    assert len(contacts) == 1
    row = contacts[(CUSTOMER, REF)]
    assert row["primeiro_contacto"] == first_day
    assert row["rgpd"] == "sim"


def test_same_customer_two_properties_are_two_rows(service):
    other = "OUTRO_REF"
    profile = json.loads((TEMPLATES / "profile.example.json").read_text(encoding="utf-8"))
    profile["property"]["reference"] = other
    profile["match"]["subject_property_reference_equals"] = other
    save_json(service.folder / "properties" / other / "profile.json", profile)
    read(service, [lead("1", ref=REF), lead("2", ref=other)])
    assert set(load_contacts(service.folder)) == {(CUSTOMER, REF), (CUSTOMER, other)}


def test_no_properties_never_writes_contacts(tmp_path):
    save_json(tmp_path / "config.json", {"account": "owner@example.com", "lookback_days": 2})
    service = MailService(tmp_path)
    read(service, [{"gmail_message_id": "1", "from": [{"email": "x@example.com"}],
                    "subject": "Olá", "body_text": "Interesse"}])
    assert not (service.folder / "contactos.csv").exists()


def test_add_contacts_fills_blank_fields_without_overwriting(tmp_path):
    add_contacts(tmp_path, [{"email": "a@example.com", "nome": "", "telefone": "",
                             "primeiro_contacto": "2026-09-01", "imovel": REF, "fonte": "Idealista"}])
    add_contacts(tmp_path, [{"email": "a@example.com", "nome": "Ana", "telefone": "900000001",
                             "primeiro_contacto": "2026-09-20", "imovel": REF, "fonte": "Idealista"}])
    row = load_contacts(tmp_path)[("a@example.com", REF)]
    assert row["nome"] == "Ana" and row["telefone"] == "900000001"
    # primeiro_contacto and the RGPD fields belong to the first sighting only.
    assert row["primeiro_contacto"] == "2026-09-01"


def test_add_contacts_with_no_entries_leaves_no_file(tmp_path):
    add_contacts(tmp_path, [])
    assert not (tmp_path / "contactos.csv").exists()
