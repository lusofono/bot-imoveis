import json
from datetime import date, timedelta
from unittest.mock import patch
import pytest
from backend.ai import parse_visits
from backend.store import load_visits
from test_properties import REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

DAY = (date.today() + timedelta(days=1)).isoformat()


def customer(key, email):
    """A portal notice from one fictitious customer."""
    return lead(key, reply_to=(email,), body_email=email)


def item(service, key):
    return next(e for e in service.pending()["properties"][0]["emails"] if e["id"] == key)


def test_each_read_can_look_further_back(service):
    with patch("backend.service.app_password", return_value="fake"), patch(
            "backend.service.read_messages", return_value=([], 0, "INBOX")) as fetch:
        service.read(days=30)
    assert fetch.call_args.args[3] == (date.today() - timedelta(days=30)).isoformat()
    with pytest.raises(ValueError, match="dias para trás"):
        service.read(days=0)


def test_the_proposal_goes_to_every_customer_except_who_declined_or_waits(service):
    for key, email in (("1", "a@example.com"), ("2", "b@example.com"), ("3", "c@example.com")):
        read(service, [customer(key, email)])
        draft_and_send(service, key, "Olá.")
    # B can only visit on another date; C wrote again and is waiting for our answer.
    queue = service.load(REF)
    queue["conversations"]["b@example.com"]["visit"] = "outra_data"
    service.save(queue, REF)
    sent_to_c = queue["conversations"]["c@example.com"]["sent_message_ids"][-1]
    read(service, [{"gmail_message_id": "c2", "from": [{"email": "c@example.com"}], "in_reply_to": sent_to_c,
                    "subject": "Re: resposta", "body_text": "Tenho uma pergunta."}])

    customers = {c["email"]: c["state"] for c in service.visit_candidates()["customers"]}
    assert customers == {"a@example.com": "ok", "b@example.com": "outra_data", "c@example.com": "pending"}
    with pytest.raises(ValueError, match="email por responder"):
        service.propose_visits(REF, DAY, "17:00", "19:00", ["c@example.com"])
    with pytest.raises(ValueError, match="já passou"):
        service.propose_visits(REF, "2020-01-01", "17:00", "19:00", ["a@example.com"])

    # The owner may still include B: the page only leaves them unticked.
    result = service.propose_visits(REF, DAY, "17:00", "19:00", ["a@example.com", "b@example.com"])
    assert result["created"] == 2
    [proposal] = [e for e in service.pending()["properties"][0]["emails"]
                  if e.get("kind") == "visit_proposal" and e["recipient"]["email"] == "a@example.com"]
    assert proposal["interaction"] == 3 and proposal["visit_window"]["start"] == "17:00"
    # It answers our last email to A, so it lands in A's own conversation.
    last_to_a = service.load(REF)["conversations"]["a@example.com"]["sent_message_ids"][-1]
    draft_and_send(service, proposal["id"], "Pode visitar amanhã entre as 17h e as 19h?")
    assert SMTP.sent[0]["In-Reply-To"] == last_to_a and SMTP.sent[0]["Subject"].startswith("Re: ")
    assert service.load(REF)["conversations"]["a@example.com"]["stage"] == 3


def test_booking_takes_free_times_on_the_grid_and_never_twice(service):
    for key, email in (("1", "a@example.com"), ("2", "b@example.com")):
        read(service, [customer(key, email)])
        draft_and_send(service, key, "Olá.")
    service.propose_visits(REF, DAY, "17:00", "19:00", ["a@example.com", "b@example.com"])
    for proposal in [e for e in service.pending()["properties"][0]["emails"] if e.get("kind") == "visit_proposal"]:
        draft_and_send(service, proposal["id"], "Proposta de visita.")
        last = service.load(REF)["conversations"][proposal["recipient"]["email"]]["sent_message_ids"][-1]
        read(service, [{"gmail_message_id": "r" + proposal["recipient"]["email"][0],
                        "from": [{"email": proposal["recipient"]["email"]}], "in_reply_to": last,
                        "subject": "Re: visita", "body_text": "Posso às 17h30."}])
    assert {item(service, key)["interaction"] for key in ("ra", "rb")} == {4}
    assert "horas livres 17:00, 17:30, 18:00, 18:30" in service.pending()["properties"][0]["instructions"]

    revision = service.pending()["properties"][0]["revision"]
    for wrong in (f"{DAY} 17:15", f"{DAY} 19:00"):
        with pytest.raises(ValueError, match="intervalo proposto"):
            service.drafts([], revision, REF, [{"id": "ra", "visit_slot": wrong}])
    service.drafts([{"id": "ra", "reply_text": "Fica marcado às 17h30."}], revision, REF,
                   [{"id": "ra", "visit_slot": f"{DAY} 17:30"}])
    revision = service.pending()["properties"][0]["revision"]
    with pytest.raises(ValueError, match="já está marcada"):
        service.drafts([], revision, REF, [{"id": "rb", "visit_slot": f"{DAY} 17:30"}])

    preview = service.preview(["ra"])
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.send(preview["preview_token"], True)
    agenda = load_visits(service.folder, REF)
    assert [(slot["at"], slot["customer"]) for slot in agenda["slots"]] == [(f"{DAY} 17:30", "a@example.com")]
    assert "horas livres 17:00, 18:00, 18:30" in service.pending()["properties"][0]["instructions"]
    customers = {c["email"]: c["state"] for c in service.visit_candidates()["customers"]}
    assert customers["a@example.com"] == "booked"


def test_the_pasted_answer_carries_visit_fields():
    queue = {"emails": [{"id": "1843212345678901234"}]}
    answer_text = json.dumps({"respostas": [{"id": "1843212345678901234", "reply_text": "Olá",
                                             "visita": f"{DAY}  17:30", "visita_estado": "nao_quer"}]})
    assert parse_visits(answer_text, queue) == [{"id": "1843212345678901234", "visit_slot": f"{DAY} 17:30",
                                                 "visit_status": "nao_quer"}]
    with pytest.raises(ValueError, match="visita_estado"):
        parse_visits(json.dumps([{"id": "1843212345678901234", "visita_estado": "talvez"}]), queue)


def test_visit_settings_live_in_the_voice(service):
    choices = {"greeting": "formal", "languages": "pt_en_fr", "closing": "cordial", "signature": "Equipa Teste",
               "visits": {"slot_minutes": 30, "rental": "15 a 20 minutos", "sale": "30 a 40 minutos"}}
    service.save_voice(choices)
    assert service.settings()["voice"]["visits"] == {"slot_minutes": 30, "rental": "15 a 20 minutos",
                                                     "sale": "30 a 40 minutos"}
    with pytest.raises(ValueError, match="10 a 180"):
        service.save_voice({**choices, "visits": {"slot_minutes": 5}})
    # Without a window to come, the assistant gets no visit section at all.
    assert "- Marcam-se de" not in service.pending()["properties"][0]["instructions"]
