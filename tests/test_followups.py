from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from backend.store import load_contacts, load_visits
from test_properties import CUSTOMER, REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

VOICE_BASE = {"greeting": "formal", "languages": "pt_en_fr", "closing": "cordial", "signature": "Equipa Teste"}


def backdate(service, ref, email, hours):
    data = service.load(ref)
    data["conversations"][email]["last_sent_at"] = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    service.save(data, ref)


def send_prepared(service, key):
    """Preview and send a draft as it already stands, without redrafting it."""
    preview = service.preview([key])
    SMTP.sent = []
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        return service.send(preview["preview_token"], True)


def item(service, key):
    return next(e for e in service.pending()["properties"][0]["emails"] if e["id"] == key)


def test_reminders_at_2_and_4_days_then_stop_at_two(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    service.save_voice({**VOICE_BASE, "reminders": {"day2": "Ainda por aqui?", "day4": "Última tentativa."}})
    backdate(service, REF, CUSTOMER, 100)  # past both the 2-day and the 4-day threshold

    read(service, [])
    reminders = [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "reminder"]
    [day2] = reminders
    assert day2["reminder"] == "2d" and day2["reply_status"] == "draft"
    assert day2["reply_text"] == "Ainda por aqui?\n\nOlá, Ana."
    send_prepared(service, day2["id"])
    conversation = service.load(REF)["conversations"][CUSTOMER]
    assert conversation["reminders_sent"] == ["2d"]
    assert conversation["last_sent_at"]  # untouched: still the backdated real last exchange... but never bumped by the reminder

    read(service, [])
    reminders = [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "reminder"]
    [day4] = reminders
    assert day4["reminder"] == "4d" and day4["reply_text"] == "Última tentativa.\n\nAinda por aqui?\n\nOlá, Ana."
    send_prepared(service, day4["id"])
    assert service.load(REF)["conversations"][CUSTOMER]["reminders_sent"] == ["2d", "4d"]

    read(service, [])  # no máximo dois: nothing more, ever
    assert not [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "reminder"]


def test_reminder_skipped_while_customer_has_not_answered_pending_email(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    service.save_voice({**VOICE_BASE, "reminders": {"day2": "Ainda por aqui?", "day4": ""}})
    backdate(service, REF, CUSTOMER, 60)
    last = service.load(REF)["conversations"][CUSTOMER]["sent_message_ids"][-1]

    # The customer wrote back in the same read a reminder would otherwise be due.
    read(service, [{"gmail_message_id": "2", "from": [{"name": "Ana Exemplo", "email": CUSTOMER}],
                    "in_reply_to": last, "subject": "Re: resposta", "body_text": "Ainda tenho uma dúvida."}])
    assert not [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "reminder"]


def test_dismissed_reminder_stops_future_ones(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    service.save_voice({**VOICE_BASE, "reminders": {"day2": "Ainda por aqui?", "day4": "Última tentativa."}})
    backdate(service, REF, CUSTOMER, 100)

    read(service, [])
    [day2] = [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "reminder"]
    revision = service.pending()["properties"][0]["revision"]
    service.dismiss([day2["id"]], revision, REF)
    assert service.load(REF)["conversations"][CUSTOMER]["reminders_stopped"] is True

    read(service, [])
    assert not [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "reminder"]


def test_close_visits_drafts_for_everyone_then_autoreplies_new_leads(service):
    other = "outro@example.com"
    read(service, [lead("1"), lead("2", reply_to=(other,), body_email=other)])
    draft_and_send(service, "1", "Olá, Ana.")  # A: already answered
    # B (other) stays pending, never drafted.

    with pytest.raises(ValueError, match="Escreve o texto"):
        service.close_visits(REF)
    service.save_voice({**VOICE_BASE, "visits_closed": "Obrigado pelo interesse; as visitas já fecharam."})

    result = service.close_visits(REF)
    assert result["drafted"] == 2
    queue = service.pending()["properties"][0]
    pending_item = next(e for e in queue["emails"] if e["recipient"]["email"] == other)
    assert (pending_item["reply_text"], pending_item["reply_status"], pending_item["closing"]) == (
        "Obrigado pelo interesse; as visitas já fecharam.", "draft", True)
    closed_item = next(e for e in queue["emails"] if e["kind"] == "visits_closed")
    assert closed_item["recipient"]["email"] == CUSTOMER and closed_item["reply_text"] == (
        "Obrigado pelo interesse; as visitas já fecharam.")
    assert load_visits(service.folder, REF)["closed_at"]

    with pytest.raises(ValueError, match="fechadas"):
        service.close_visits(REF)
    with pytest.raises(ValueError, match="fechadas"):
        service.visit_candidates(REF)

    # A brand new lead for this property is auto-drafted, never left pending.
    read(service, [lead("3", reply_to=("terceiro@example.com",), body_email="terceiro@example.com")])
    new_item = next(e for e in service.pending()["properties"][0]["emails"] if e["id"] == "3")
    assert (new_item["reply_status"], new_item["reply_text"], new_item["closing"]) == (
        "draft", "Obrigado pelo interesse; as visitas já fecharam.", True)


def test_close_visits_leaves_an_uncertain_send_untouched(service):
    read(service, [lead("1")])
    service.drafts([{"id": "1", "reply_text": "Olá, Ana."}], service.pending()["properties"][0]["revision"])
    preview = service.preview(["1"])

    class Failing:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def login(self, *a): pass
        def send_message(self, msg): raise ConnectionError("boom")

    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", Failing):
        service.send(preview["preview_token"], True)
    assert item(service, "1")["reply_status"] == "uncertain"

    service.save_voice({**VOICE_BASE, "visits_closed": "Obrigado pelo interesse; as visitas já fecharam."})
    result = service.close_visits(REF)
    # An uncertain send is never redrafted, and the customer gets no second, synthetic closing email either.
    assert result["drafted"] == 0
    still = item(service, "1")
    assert (still["reply_status"], still["reply_text"]) == ("uncertain", "Olá, Ana.")
    assert not [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "visits_closed"]


def test_consent_request_suggestion_and_confirmation_record_rgpd(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")

    with pytest.raises(ValueError, match="Escreve o texto"):
        service.request_consent(REF)
    service.save_voice({**VOICE_BASE, "consent_request": "Podemos guardar o seu contacto? Responda sim."})

    result = service.request_consent(REF)
    assert result["drafted"] == 1
    assert service.load(REF)["conversations"][CUSTOMER]["consent_asked"] is True
    # Asking again does not repeat it.
    assert service.request_consent(REF)["drafted"] == 0

    [consent_item] = [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "consent_request"]
    send_prepared(service, consent_item["id"])
    last = service.load(REF)["conversations"][CUSTOMER]["sent_message_ids"][-1]

    read(service, [{"gmail_message_id": "2", "from": [{"name": "Ana Exemplo", "email": CUSTOMER}],
                    "in_reply_to": last, "subject": "Re: consentimento", "body_text": "Sim, pode guardar."}])
    [reply] = [e for e in service.pending()["properties"][0]["emails"] if e["id"] == "2"]
    assert reply["consent_suggested"] is True

    service.confirm_consent("2", REF)
    row = load_contacts(service.folder)[(CUSTOMER, REF)]
    assert row["rgpd"] == "sim" and row["rgpd_data"] and row["rgpd_prova"]
    assert service.load(REF)["conversations"][CUSTOMER]["consent"] == "sim"
    confirmed = item(service, "2")
    assert confirmed["consent_suggested"] is False and confirmed["consent_confirmed"] is True
