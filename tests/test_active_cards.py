"""«Enviados ficam na fila»: the active customers already answered stay in view, with «Escrever mais»."""
from datetime import date, timedelta
from backend.ai import reply_prompt
from backend.store import load_visits, save_visits
from test_properties import REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

DAY = (date.today() + timedelta(days=2)).isoformat()


def queue(service):
    return service.pending()["properties"][0]


def test_an_answered_customer_stays_as_a_sent_card_until_a_visit_is_booked(service):
    read(service, [lead("1", reply_to=("a@example.com",), body_email="a@example.com"),
                   lead("2", reply_to=("b@example.com",), body_email="b@example.com")])
    assert queue(service)["active"] == []  # nobody answered yet
    draft_and_send(service, "1", "Olá, Ana.")
    [card] = queue(service)["active"]
    assert (card["email"], card["stage"], card["last_text"]) == ("a@example.com", 1, "Olá, Ana.")
    # Taken out by the owner: gone, until that conversation moves again.
    service.remove_active(REF, "a@example.com")
    assert queue(service)["active"] == []
    draft_and_send(service, "2", "Olá.")
    assert [c["email"] for c in queue(service)["active"]] == ["b@example.com"]
    # A booked visit ends the card.
    agenda = load_visits(service.folder, REF)
    agenda["slots"].append({"at": f"{DAY} 15:00", "customer": "b@example.com"})
    save_visits(service.folder, REF, agenda)
    assert queue(service)["active"] == []


def test_write_more_is_a_draft_in_the_conversation_that_spends_no_step(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    email = queue(service)["active"][0]["email"]
    key = service.write_more(REF, email)["id"]
    current = queue(service)
    [item] = current["emails"]
    assert item["id"] == key and item["kind"] == "addition" and item["interaction"] == 1
    assert current["active"] == []  # the customer now has an email in the queue
    prompt = reply_prompt(current, [key], "Diz que o estacionamento está incluído.")
    assert "interação: acrescento" in prompt and "estacionamento" in prompt
    draft_and_send(service, key, "Acrescento: o estacionamento está incluído.")
    conversation = service.load(REF)["conversations"][email]
    assert conversation["stage"] == 1 and conversation["last_text"] == "Acrescento: o estacionamento está incluído."
    assert SMTP.sent[-1]["Subject"].startswith("Re: ")
    assert [c["email"] for c in queue(service)["active"]] == [email]  # back as a sent card
