import json
from pathlib import Path
from unittest.mock import patch
import pytest
from bot_mail.cli import main
from bot_mail.properties import clean_property, load_voice
from bot_mail.service import MailService
from bot_mail.storage import save_json

ROOT = Path(__file__).resolve().parent.parent
REF = "REF_IMOVEL"
IDEALISTA = {"name": "idealista", "email": "reply@idealista.pt"}
CUSTOMER = "ana.exemplo@example.com"


@pytest.fixture
def service(tmp_path):
    save_json(tmp_path / "config.json", {"account": "owner@example.com", "lookback_days": 2})
    profile = json.loads((ROOT / "apalace/rent/properties/profile.example.json").read_text(encoding="utf-8"))
    save_json(tmp_path / "properties" / REF / "profile.json", profile)
    voice = json.loads((ROOT / "apalace/rent/voice.json").read_text(encoding="utf-8"))
    # Explicit choices, so the tests do not depend on the owner's current voice.
    for key, choice in (("greeting", "formal"), ("languages", "pt_en_fr"), ("closing", "cordial")):
        voice["style"][key]["selected"] = choice
    save_json(tmp_path / "voice.json", voice)
    return MailService(tmp_path)


def lead(key, reply_to=(CUSTOMER,), ref=REF, listing="00000000", body_email=CUSTOMER, sender=IDEALISTA):
    """A portal notice as read_messages returns it (fictitious customer)."""
    body = "\n".join(["Tens uma nova mensagem que aguarda resposta", "Ana Exemplo", "900 000 001", body_email,
                      "Bom dia, gostaria de visitar o imóvel.", "Pode ser ao fim da tarde?",
                      f"Ref. {ref} | Anunciante", f"Código do anúncio: {listing}", "1.000 €",
                      "Se fores contactado por chat, tenta responder por chat."])
    return {"gmail_message_id": key, "thread_id": f"t{key}", "message_id": f"<{key}@portal.example>",
            "from": [sender], "reply_to": [{"name": "", "email": address} for address in reply_to],
            "subject": f"🤩 Nova mensagem (com perfil) de Ana Exemplo sobre o teu imóvel, com ref: {ref} | Anunciante",
            "body_text": body, "body_truncated": False}


def read(service, messages):
    with patch("bot_mail.service.app_password", return_value="fake"), patch(
            "bot_mail.service.read_messages", return_value=(messages, len(messages), "INBOX")):
        return service.read()


class SMTP:
    sent = []
    def __init__(self, *args, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def login(self, *args): pass
    def send_message(self, msg):
        self.sent.append(msg)
        return {}


def draft_and_send(service, key, text="Olá, Ana."):
    service.drafts([{"id": key, "reply_text": text}], service.pending()["properties"][0]["revision"])
    preview = service.preview([key])
    SMTP.sent = []
    with patch("bot_mail.service.app_password", return_value="fake"), patch("bot_mail.service.smtplib.SMTP_SSL", SMTP):
        return service.send(preview["preview_token"], True)


def test_lead_is_extracted_into_its_property_queue_and_answered_at_reply_to(service):
    unrelated = {"gmail_message_id": "x", "from": [{"email": "news@example.com"}], "subject": f"Promo {REF}"}
    queue = read(service, [lead("1"), unrelated])["properties"][0]
    assert (queue["property_ref"], queue["added"]) == (REF, 1)
    [email] = queue["emails"]
    assert email["customer"] == {"name": "Ana Exemplo", "email": CUSTOMER, "phone": "900 000 001",
                                 "message": "Bom dia, gostaria de visitar o imóvel.\nPode ser ao fim da tarde?"}
    assert (email["recipient"]["email"], email["blocked"], email["interaction"], email["warnings"]) == (
        CUSTOMER, None, 1, [])
    for expected in ("Equipa APalace Imobiliária", "situação profissional", "Obrigado pelo seu contacto.", REF):
        assert expected in queue["instructions"]
    assert (service.folder / "properties" / REF / "queue.json").exists() and not service.path.exists()

    assert draft_and_send(service, "1")["remaining"] == 0
    assert SMTP.sent[0]["To"] == CUSTOMER and SMTP.sent[0]["In-Reply-To"] == "<1@portal.example>"
    conversation = service.load(REF)["conversations"][CUSTOMER]
    assert conversation["stage"] == 1 and conversation["thread_ids"] == ["t1"]

    # Same customer again through the portal, and a direct answer to our email: both are the 2nd interaction.
    answer = {"gmail_message_id": "3", "from": [{"name": "Ana Exemplo", "email": CUSTOMER}],
              "in_reply_to": str(SMTP.sent[0]["Message-ID"]), "subject": "Re: Nova mensagem",
              "body_text": "Sou enfermeira.\n\nOn Thu, 17 Sep 2026, Owner <owner@example.com> wrote:\n> Olá, Ana."}
    emails = {e["id"]: e for e in read(service, [lead("2"), answer])["properties"][0]["emails"]}
    assert emails["2"]["interaction"] == emails["3"]["interaction"] == 2
    assert (emails["3"]["kind"], emails["3"]["recipient"]["email"]) == ("follow_up", CUSTOMER)
    assert emails["3"]["customer"]["message"] == "Sou enfermeira."
    assert any("outro email pendente" in warning for warning in emails["3"]["warnings"])


@pytest.mark.parametrize("reply_to, notice", [
    ((), "não tem Reply-To"),
    (("a@example.com", "b@example.com"), "não identifica um único"),
    (("reply@idealista.pt",), "não identifica um único"),
    (("owner@example.com",), "não identifica um único"),
])
def test_missing_or_invalid_reply_to_blocks_sending_until_dismissed(service, reply_to, notice):
    queue = read(service, [lead("1", reply_to=reply_to)])["properties"][0]
    [email] = queue["emails"]
    assert notice in email["blocked"] and email["recipient"] is None and email["interaction"] is None
    service.drafts([{"id": "1", "reply_text": "Olá"}], queue["revision"])
    with pytest.raises(ValueError, match="bloqueado"):
        service.preview(["1"])
    revision = service.pending()["properties"][0]["revision"]
    assert service.dismiss(["1"], revision)["dismissed"] == 1
    assert read(service, [lead("1", reply_to=reply_to)])["properties"][0]["added"] == 0
    assert service.load(REF)["conversations"] == {}


def test_headers_decide_which_texts_are_downloaded(service):
    read(service, [lead("1")])
    with patch("bot_mail.service.app_password", return_value="fake"), patch(
            "bot_mail.service.read_messages", return_value=([], 0, "INBOX")) as fetch:
        service.read()
    accept = fetch.call_args.kwargs["accept"]
    unrelated = {"gmail_message_id": "9", "from": [{"email": "news@example.com"}], "subject": "Promo"}
    assert (accept(lead("1")), accept(lead("2")), accept(unrelated)) == (False, True, False)


def test_only_the_exact_reference_from_the_portal_sender_counts(service):
    messages = [lead("1", ref=REF + "2"), lead("2", sender={"name": "idealista", "email": "outro@idealista.pt"}),
                lead("3", sender={"name": "Outro nome", "email": "reply@idealista.pt"})]
    assert [e["id"] for e in read(service, messages)["properties"][0]["emails"]] == ["3"]


def test_conflicting_identifiers_are_warnings_for_manual_review(service):
    [email] = read(service, [lead("1", listing="99999999", body_email="outra@example.com")])["properties"][0]["emails"]
    assert email["recipient"]["email"] == CUSTOMER
    assert any("99999999" in w for w in email["warnings"]) and any("outra@example.com" in w for w in email["warnings"])


def test_follow_up_from_another_address_is_blocked(service):
    read(service, [lead("1")])
    draft_and_send(service, "1")
    stranger = {"gmail_message_id": "2", "thread_id": "t1", "from": [{"email": "familiar@example.com"}],
                "subject": "Re: Nova mensagem", "body_text": "Olá"}
    [email] = read(service, [stranger])["properties"][0]["emails"]
    assert (email["kind"], email["recipient"]) == ("follow_up", None) and "ambígua" in email["blocked"]


def test_voice_comes_from_the_json_and_is_required(service, capsys):
    voice = json.loads((service.folder / "voice.json").read_text(encoding="utf-8"))
    voice["style"]["greeting"]["selected"] = "cordial"
    save_json(service.folder / "voice.json", voice)
    text = service.pending()["properties"][0]["instructions"]
    assert "Olá, {customer_name}." in text and "Exmo." not in text
    voice["style"]["greeting"]["selected"] = None
    voice["style"]["signature"]["text"] = ""
    save_json(service.folder / "voice.json", voice)
    with pytest.raises(ValueError, match="falta: saudação, assinatura"):
        service.pending()
    # Without the voice the server does not start either.
    assert main(["--instance", str(service.folder), "serve"]) == 1
    assert "Configura a voz" in capsys.readouterr().err


def test_the_owners_voice_is_complete():
    # The published voice.json must pass the same validation the server runs at start.
    assert load_voice(ROOT / "apalace/rent")["style"]["signature"]["text"]


def test_several_properties_need_property_ref(service):
    profile = json.loads((service.folder / "properties" / REF / "profile.json").read_text(encoding="utf-8"))
    profile["property"]["reference"] = profile["match"]["subject_property_reference_equals"] = "OUTRO"
    save_json(service.folder / "properties" / "OUTRO" / "profile.json", profile)
    result = read(service, [lead("1"), lead("2", ref="OUTRO")])
    assert {queue["property_ref"]: queue["added"] for queue in result["properties"]} == {REF: 1, "OUTRO": 1}
    with pytest.raises(ValueError, match="property_ref"):
        service.drafts([{"id": "1", "reply_text": "x"}], 1)
    revision = service.pending(REF)["properties"][0]["revision"]
    assert service.drafts([{"id": "1", "reply_text": "x"}], revision, REF)["saved"] == 1
    with pytest.raises(ValueError, match="property_ref"):
        service.pending("../../secrets")


def test_property_folder_without_profiles_refuses_instead_of_reading_everything(tmp_path, capsys):
    # Profiles are not in Git: a server clone without them must not import the whole mailbox.
    save_json(tmp_path / "config.json", {"account": "owner@example.com"})
    save_json(tmp_path / "voice.json", json.loads((ROOT / "apalace/rent/voice.json").read_text(encoding="utf-8")))
    with patch("bot_mail.service.read_messages") as fetch, pytest.raises(ValueError, match="Copia os perfis"):
        MailService(tmp_path).read()
    fetch.assert_not_called()
    assert main(["--instance", str(tmp_path), "serve"]) == 1
    assert "Copia os perfis" in capsys.readouterr().err


def test_profile_of_another_account_is_rejected(service):
    save_json(service.folder / "config.json", {"account": "other@example.com"})
    with pytest.raises(ValueError, match="outra conta"):
        service.pending()


@pytest.mark.parametrize("rent, euros", [
    ("1.500 €", 1500), ("1500", 1500), (1500, 1500), (850.5, 850.5), ("850.00", 850), ("850,50 €", 850.5),
    ("1,200", 1200), ("1.200,50", 1200.5), ("1,200.50", 1200.5), ("1 500 €/mês", 1500),
    (None, None), ("sob consulta", None),
])
def test_rent_in_portuguese_or_english_notation(rent, euros):
    fields = clean_property({"reference": REF, "description": "T2", "advertised_rent_eur": rent})
    assert fields["advertised_rent_eur"] == euros


@pytest.mark.parametrize("rent", ["1500 € + 50 € de condomínio", "12.34.56", "1,234.567", "1.500.000", True])
def test_ambiguous_or_impossible_rent_is_refused(rent):
    with pytest.raises(ValueError, match="Renda"):
        clean_property({"reference": REF, "description": "T2", "advertised_rent_eur": rent})
