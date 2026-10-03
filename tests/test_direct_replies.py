"""Replies the owner writes straight from Gmail: READ finds them in All Mail and the page takes them into account."""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from test_properties import CUSTOMER, REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

NOW = datetime.now(timezone.utc)


def at(hours_ago):
    return (NOW - timedelta(hours=hours_ago)).isoformat()


def direct(key, hours_ago, text, thread="t1", to=CUSTOMER):
    """The owner's own reply, as read_messages hands it over in the outgoing list."""
    return {"gmail_message_id": f"g{key}", "thread_id": thread, "message_id": f"<{key}@mail.gmail.com>",
            "date": at(hours_ago), "from": [{"name": "Equipa", "email": "owner@example.com"}],
            "to": [{"name": "Ana Exemplo", "email": to}], "cc": [], "subject": "Re: Nova mensagem", "body_text": text}


def read_with_sent(service, incoming, sent):
    def fake(*args, accept=None, outgoing=None, accept_outgoing=None, **kwargs):
        if outgoing is not None:
            outgoing.extend(message for message in sent if accept_outgoing(message))
        return [message for message in incoming if not accept or accept(message)], len(incoming), "[Gmail]/All Mail"
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.read_messages", side_effect=fake):
        return service.read()


def events(service):
    return [json.loads(line) for line in (service.folder / "logs" / "events.jsonl").read_text().splitlines()]


def test_a_reply_written_in_gmail_keeps_the_email_in_the_queue_marked_and_with_the_context(service):
    read(service, [dict(lead("1"), date=at(5))])
    reply = direct("d1", 2, "Olá Ana, pode visitar amanhã às 18:00.\n\nEm qui., 24/09/2026 às 10:00, Ana <\n"
                            "ana.exemplo@example.com> escreveu:\n> Bom dia, gostaria de visitar o imóvel.")
    result = read_with_sent(service, [], [reply])
    assert result["direct"] == 1
    # Nothing leaves the queue: the owner may still add something, or take it out.
    [kept] = service.pending()["properties"][0]["emails"]
    assert kept["id"] == "1" and kept["interaction"] == 1
    assert any("diretamente no Gmail" in warning for warning in kept["warnings"])
    assert kept["history"][-1]["text"] == "Olá Ana, pode visitar amanhã às 18:00."
    conversation = service.load(REF)["conversations"][CUSTOMER]
    assert conversation["stage"] == 1 and conversation["name"] == "Ana Exemplo"  # the Gmail reply was that step
    last = conversation["history"][-1]
    assert (last["who"], last["text"], last["at"]) == ("nos", "Olá Ana, pode visitar amanhã às 18:00.", at(2)[:10])
    assert last["ts"][:16] == datetime.fromisoformat(at(2)).astimezone(timezone.utc).isoformat()[:16]
    # «Email completo» shows the whole conversation: our reply in Gmail comes after the customer's email.
    assert [turn["who"] for turn in kept["conversation"]][-2:] == ["cliente", "nos"]
    assert "<d1@mail.gmail.com>" in conversation["sent_message_ids"]
    [sent] = [event for event in events(service) if event["event"] == "send"]
    assert (sent["kind"], sent["reference"], sent["waited_hours"]) == ("direct", REF, 3.0)

    # Read again: the same reply is never counted twice.
    assert read_with_sent(service, [], [reply])["direct"] == 0
    assert service.load(REF)["conversations"][CUSTOMER]["stage"] == 1

    # One more email to it from the page is an addition: it goes out, but spends no second step.
    draft_and_send(service, "1", "Acrescento: o estacionamento está incluído.")
    assert service.load(REF)["conversations"][CUSTOMER]["stage"] == 1
    assert [event["waited_hours"] for event in events(service) if event["event"] == "send"][-1] is None

    # The customer answers the reply written in Gmail: a follow-up, the 2nd interaction, with the context.
    read(service, [{"gmail_message_id": "c2", "thread_id": "t1", "from": [{"email": CUSTOMER}],
                    "in_reply_to": "<d1@mail.gmail.com>", "subject": "Re: Re: Nova mensagem", "body_text": "Combinado."}])
    [answer] = service.pending()["properties"][0]["emails"]
    assert answer["interaction"] == 2
    assert any(turn["who"] == "nos" and "18:00" in turn["text"] for turn in answer["history"])


def test_a_message_the_page_sent_is_never_taken_for_a_direct_reply(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    sent_id = service.load(REF)["conversations"][CUSTOMER]["sent_message_ids"][-1]
    echo = dict(direct("x", 0, "Olá, Ana."), message_id=sent_id)
    assert read_with_sent(service, [], [echo])["direct"] == 0
    assert service.load(REF)["conversations"][CUSTOMER]["stage"] == 1


def test_a_reply_older_than_the_customers_new_email_leaves_it_waiting_with_the_context(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    ours = service.load(REF)["conversations"][CUSTOMER]["sent_message_ids"][-1]
    # In one read: the owner wrote from Gmail 3 hours ago, and the customer answered an hour ago.
    later = {"gmail_message_id": "c2", "thread_id": "t1", "date": at(1), "from": [{"email": CUSTOMER}],
             "in_reply_to": ours, "subject": "Re: Nova mensagem", "body_text": "Obrigada, e o estacionamento?"}
    result = read_with_sent(service, [later], [direct("d2", 3, "Já agora: a renda inclui o condomínio.")])
    assert result["direct"] == 1
    [waiting] = service.pending()["properties"][0]["emails"]
    assert waiting["id"] == "c2" and waiting["interaction"] == 2  # nothing pending was answered: no extra step
    assert "Já agora: a renda inclui o condomínio." in [turn["text"] for turn in waiting["history"]]
    # Same day, but in their real order: the reply in Gmail (3 h ago) before the customer's email (1 h ago).
    texts = [turn["text"] for turn in waiting["conversation"]]
    assert texts.index("Já agora: a renda inclui o condomínio.") < texts.index("Obrigada, e o estacionamento?")


def test_mail_to_someone_the_page_does_not_know_is_left_alone(service):
    read(service, [lead("1")])
    stranger = direct("d3", 1, "Olá.", thread="t999", to="outra.pessoa@example.com")
    assert read_with_sent(service, [], [stranger])["direct"] == 0
    assert len(service.pending()["properties"][0]["emails"]) == 1
