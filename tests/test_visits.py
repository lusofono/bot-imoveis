import json
from datetime import date, timedelta
from unittest.mock import patch
import pytest
from backend.ai import parse_visits, reply_prompt
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


def test_the_proposal_carries_the_conversation_history_into_the_prompt(service):
    read(service, [customer("1", "a@example.com")])
    draft_and_send(service, "1", "Olá, claro, pode ser ao fim da tarde.")
    service.propose_visits(REF, DAY, "17:00", "19:00", ["a@example.com"])
    [proposal] = [e for e in service.pending()["properties"][0]["emails"] if e.get("kind") == "visit_proposal"]
    assert proposal["history"] and proposal["history"][-1]["text"] == "Olá, claro, pode ser ao fim da tarde."
    queue = service.pending()["properties"][0]
    prompt = reply_prompt(queue, [proposal["id"]])
    assert "Histórico desta conversa" in prompt and "Olá, claro, pode ser ao fim da tarde." in prompt
    # Never "Mensagem nova": nothing new came from the client, it is us proposing the visit.
    assert "Mensagem nova:" not in prompt and "Mensagem:" in prompt


def test_the_round_summary_shows_who_it_went_to_and_where_each_one_stands(service):
    for key, email in (("1", "a@example.com"), ("2", "b@example.com")):
        read(service, [customer(key, email)])
        draft_and_send(service, key, "Olá.")
    service.propose_visits(REF, DAY, "17:00", "19:00", ["a@example.com", "b@example.com"])

    summary = service.visit_round_summary(REF)
    assert summary["window"]["day"] == DAY and summary["window"]["start"] == "17:00"
    by_email = {r["email"]: r for r in summary["recipients"]}
    assert set(by_email) == {"a@example.com", "b@example.com"}
    # Not sent yet: the proposal itself is the "email por responder" candidates() sees.
    assert by_email["a@example.com"]["state"] == "pending" and by_email["a@example.com"]["visit_at"] is None

    proposal = next(e for e in service.pending()["properties"][0]["emails"]
                    if e.get("kind") == "visit_proposal" and e["recipient"]["email"] == "a@example.com")
    revision = service.pending()["properties"][0]["revision"]
    service.drafts([{"id": proposal["id"], "reply_text": "Fica marcado."}], revision, REF,
                   [{"id": proposal["id"], "visit_slot": f"{DAY} 17:30"}])
    preview = service.preview([proposal["id"]], REF)
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.send(preview["preview_token"], True, REF)

    summary = service.visit_round_summary(REF)
    by_email = {r["email"]: r for r in summary["recipients"]}
    assert by_email["a@example.com"] == {"email": "a@example.com", "name": "Ana Exemplo", "state": "booked",
                                         "reason": "já tem visita marcada", "visit_at": f"{DAY} 17:30"}
    # B's own proposal is still an unsent draft: candidates() still sees it as "tem um email por responder".
    assert by_email["b@example.com"]["state"] == "pending"


def test_an_ignored_contact_is_never_a_candidate_and_new_messages_are_dropped(service):
    read(service, [customer("1", "a@example.com")])
    draft_and_send(service, "1", "Olá.")
    assert {c["email"]: c["state"] for c in service.visit_candidates()["customers"]} == {"a@example.com": "ok"}

    result = service.set_ignored(REF, "a@example.com")
    assert result == {"property_ref": REF, "email": "a@example.com", "ignored": True, "removed": 0}
    assert service.visit_candidates()["customers"] == []
    assert service.ignored_contacts()["customers"] == [{"email": "a@example.com", "name": "Ana Exemplo", "reason": "",
                                                        "kind": "black"}]

    # They write again: silently dropped, never reaches the queue, whatever they say.
    before = len(service.pending()["properties"][0]["emails"])
    last = service.load(REF)["conversations"]["a@example.com"]["sent_message_ids"][-1]
    read(service, [{"gmail_message_id": "again", "from": [{"email": "a@example.com"}], "in_reply_to": last,
                    "subject": "Re: resposta", "body_text": "Ainda tenho interesse."}])
    assert len(service.pending()["properties"][0]["emails"]) == before

    # Un-ignoring restores them as a normal candidate.
    service.set_ignored(REF, "a@example.com", False)
    assert {c["email"] for c in service.visit_candidates()["customers"]} == {"a@example.com"}
    assert service.ignored_contacts()["customers"] == []


def test_the_ignore_reason_is_kept_to_explain_later_and_cleared_on_undo(service):
    read(service, [customer("1", "a@example.com")])
    draft_and_send(service, "1", "Olá.")
    service.set_ignored(REF, "a@example.com", True, "  Cliente disse   que não tem interesse.  ")
    [entry] = service.ignored_contacts()["customers"]
    assert entry["reason"] == "Cliente disse que não tem interesse." and entry["kind"] == "grey"

    service.set_ignored(REF, "a@example.com", False)
    service.set_ignored(REF, "a@example.com", True)  # ignored again, no reason given this time
    [entry] = service.ignored_contacts()["customers"]
    assert entry["reason"] == "" and entry["kind"] == "black"
    service.set_ignored(REF, "a@example.com", True, kind="grey")  # e.g. said so on the phone, no reason typed
    assert service.ignored_contacts()["customers"][0]["kind"] == "grey"
    assert service.metrics(14)["properties"][0]["ignored"] == {"black": 0, "grey": 1}


def test_ignoring_clears_their_pending_email_and_skips_them_when_closing_visits(service):
    read(service, [customer("1", "a@example.com")])
    draft_and_send(service, "1", "Olá.")
    read(service, [customer("2", "b@example.com")])  # still pending, never answered
    assert len(service.pending()["properties"][0]["emails"]) == 1  # only b's own lead is pending

    result = service.set_ignored(REF, "b@example.com")
    assert result["removed"] == 1
    assert service.pending()["properties"][0]["emails"] == []

    service.save_voice({"greeting": "formal", "languages": "pt_en_fr", "closing": "cordial", "signature": "Equipa",
                        "visits_closed": "As visitas a este imóvel já estão fechadas."})
    result = service.close_visits(REF)
    # Only A (never ignored, already answered) gets the closing email; B is on the ignore list.
    recipients = {(item.get("recipient") or {}).get("email") for item in service.pending()["properties"][0]["emails"]}
    assert recipients == {"a@example.com"}
    assert result["drafted"] == 1


def test_the_round_summary_is_empty_before_any_round_was_ever_proposed(service):
    assert service.visit_round_summary(REF) == {"property_ref": REF, "window": None, "recipients": []}


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


def test_analysis_prompt_carries_active_clients_history_never_json(service):
    read(service, [customer("1", "a@example.com")])
    draft_and_send(service, "1", "Olá, obrigado pelo contacto.")
    last = service.load(REF)["conversations"]["a@example.com"]["sent_message_ids"][-1]
    read(service, [{"gmail_message_id": "2", "from": [{"name": "A", "email": "a@example.com"}],
                    "in_reply_to": last, "subject": "Re: resposta", "body_text": "Só posso ao fim de semana."}])
    read(service, [customer("3", "b@example.com")])
    draft_and_send(service, "3", "Olá.")
    queue = service.load(REF)
    queue["conversations"]["b@example.com"]["visit"] = "nao_quer"
    service.save(queue, REF)

    prompt = service.visit_analysis_prompt(REF)
    assert "Só posso ao fim de semana." in prompt and "não uses JSON" in prompt
    assert "b@example.com" not in prompt and "não quer" not in prompt.split("CLIENTES")[1].split("(estado")[0]


def test_analyze_visits_uses_the_api_without_json_mode_and_logs_usage(service):
    read(service, [customer("1", "a@example.com")])
    draft_and_send(service, "1", "Olá.")
    with pytest.raises(RuntimeError, match="mac/openai_key.command"):
        service.analyze_visits(REF)
    with patch("backend.service.openai_api_key", return_value="sk-test"), \
         patch("backend.service.complete", return_value=("Resumo dos clientes.", {"prompt_tokens": 40, "completion_tokens": 15})) as complete:
        result = service.analyze_visits(REF)
    assert result == {"property_ref": REF, "summary": "Resumo dos clientes.",
                      "tokens": {"prompt_tokens": 40, "completion_tokens": 15}, "fuel": service.api_fuel(REF)}
    assert complete.call_args.kwargs == {"json_mode": False}
    events = [json.loads(line) for line in (service.folder / "logs" / "events.jsonl").read_text().splitlines()]
    assert any(e["event"] == "openai_usage" and e["prompt_tokens"] == 40 for e in events)


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
