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
    import pytest
    with pytest.raises(ValueError, match="o que queres acrescentar"):  # 05/10: never saved empty
        service.write_more(REF, email)
    key = service.write_more(REF, email, note="O estacionamento está incluído.")["id"]
    current = queue(service)
    [item] = current["emails"]
    assert item["id"] == key and item["kind"] == "addition" and item["interaction"] == 1
    assert item["addition_note"] == "O estacionamento está incluído." and not item["reply_text"]
    assert current["active"] == []  # the customer now has an email in the queue
    prompt = reply_prompt(current, [key])
    assert "interação: acrescento" in prompt and "O estacionamento está incluído." in prompt
    assert "escrito a todos" not in prompt  # one customer's, not «Escrever a todos»
    draft_and_send(service, key, "Acrescento: o estacionamento está incluído.")
    conversation = service.load(REF)["conversations"][email]
    assert conversation["stage"] == 1 and conversation["last_text"] == "Acrescento: o estacionamento está incluído."
    assert SMTP.sent[-1]["Subject"].startswith("Re: ")
    assert [c["email"] for c in queue(service)["active"]] == [email]  # back as a sent card


def test_write_to_all_makes_one_addition_for_each_active_customer_or_only_the_unanswered(service):
    # 04/10, «Escrever a todos»: the owner's words, one addition draft per customer — every active customer, or only
    # those whose last turn is ours; never the greylist, who declined or a closed contact; one with an email in the
    # queue is left out (answered there)
    people = ["a@example.com", "b@example.com", "c@example.com", "d@example.com"]
    read(service, [lead(str(n), reply_to=(email,), body_email=email) for n, email in enumerate(people, 1)])
    for n in range(1, 5):
        draft_and_send(service, str(n), "Olá.")
    data = service.load(REF)
    data["conversations"]["b@example.com"]["history"].append({"who": "cliente", "text": "Obrigado.", "at": DAY})
    data["conversations"]["c@example.com"].update(ignored=True, ignored_kind="grey")
    service.save(data, REF)
    assert queue(service)["write_all"] == {"all": 3, "unanswered": 2, "queued": 0}
    import pytest
    for audience, note, error in (("todos", "Olá", "a quem escrever"), ("all", "  ", "o que queres dizer")):
        with pytest.raises(ValueError, match=error):
            service.write_to_all(REF, audience, note)
    note = "A casa está livre a partir de terça; precisamos da disponibilidade para 7 a 9 de outubro."
    assert service.write_to_all(REF, "unanswered", note)["created"] == 2
    current = queue(service)
    made = {item["recipient"]["email"]: item for item in current["emails"]}
    assert set(made) == {"a@example.com", "d@example.com"} and all(item["kind"] == "addition" for item in made.values())
    assert current["write_all"] == {"all": 1, "unanswered": 0, "queued": 2}  # the two drafts are in the queue now
    prompt = reply_prompt(current, [made["a@example.com"]["id"]])
    assert "escrito a todos os clientes" in prompt and "7 a 9 de outubro" in prompt
    assert service.write_to_all(REF, "all", "Outra nota.")["created"] == 1  # b, who had answered
    with pytest.raises(ValueError, match="Ninguém a quem escrever"):
        service.write_to_all(REF, "all", "Mais uma.")
