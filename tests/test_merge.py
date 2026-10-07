"""Several emails from one customer in the queue are one card: one reply answers them all."""
from datetime import datetime, timedelta, timezone
from test_properties import CUSTOMER, REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)
from test_direct_replies import direct, read_with_sent

NOW = datetime.now(timezone.utc)


def at(hours_ago):
    return (NOW - timedelta(hours=hours_ago)).isoformat()


def follow_up(key, hours_ago, text, service):
    ours = service.load(REF)["conversations"][CUSTOMER]["sent_message_ids"][-1]
    return {"gmail_message_id": key, "thread_id": "t1", "date": at(hours_ago), "from": [{"name": "Ana", "email": CUSTOMER}],
            "message_id": f"<{key}@cliente>", "in_reply_to": ours, "subject": "Re: Nova mensagem", "body_text": text}


def test_one_reply_answers_every_message_and_spends_one_step(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    read(service, [follow_up("c2", 5, "Somos três pessoas.", service), follow_up("c3", 2, "E temos um gato.", service)])
    [card] = service.pending()["properties"][0]["emails"]
    assert (card["id"], card["merged_ids"], card["interaction"]) == ("c2", ["c3"], 2)
    assert card["customer"]["message"].index("Somos três") < card["customer"]["message"].index("gato")
    draft_and_send(service, "c2", "Obrigado. Aceitamos animais.")
    assert SMTP.sent[-1]["In-Reply-To"] == "<c3@cliente>"  # it answers the newest message
    queue = service.load(REF)
    assert queue["conversations"][CUSTOMER]["stage"] == 2 and {"c2", "c3"} <= set(queue["replied_message_ids"])
    assert service.pending()["properties"][0]["emails"] == []


def test_a_message_answered_in_gmail_joins_as_context_and_the_rest_is_a_new_step(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    first = follow_up("c2", 6, "Posso visitar amanhã?", service)
    read_with_sent(service, [first], [direct("d1", 5, "Pode, às 15:00.")])
    assert service.load(REF)["conversations"][CUSTOMER]["stage"] == 2  # the Gmail reply was that step
    read(service, [follow_up("c3", 1, "Afinal só posso às 16:00.", service)])
    [card] = service.pending()["properties"][0]["emails"]
    # A new step (stage 2 → the next email), but no visit was proposed yet: it is still the qualification, the 2nd.
    assert (card["id"], card["merged_ids"], card["interaction"]) == ("c3", ["c2"], 2)
    assert "answered_directly" not in card
    assert "já respondida no Gmail" in card["customer"]["message"]
    assert any("Já respondeste no Gmail" in warning for warning in card["warnings"])


def test_a_draft_written_before_the_newer_message_goes_back_to_review(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    read(service, [follow_up("c2", 5, "Qual é a renda?", service)])
    revision = service.pending()["properties"][0]["revision"]
    service.drafts([{"id": "c2", "reply_text": "A renda é 1.000 €."}], revision, REF)
    read(service, [follow_up("c3", 1, "E a caução?", service)])
    [card] = service.pending()["properties"][0]["emails"]
    assert (card["reply_status"], card["reply_text"]) == ("pending", "A renda é 1.000 €.")
    assert any("revê-o antes de enviar" in warning for warning in card["warnings"])
