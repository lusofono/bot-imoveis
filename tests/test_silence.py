"""Silence and no-shows (26/09): reminders written by the assistant, absent and inactive (06/10), and a
draft for a customer who did not come to the visit."""
from datetime import datetime, timedelta, timezone
from backend.ai import reply_prompt
from backend.store import load_visits, save_visits
from test_followups import backdate
from test_merge import follow_up
from test_properties import CUSTOMER, REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)


def reminders(service):
    return [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "reminder"]


def test_without_a_phrase_the_assistant_writes_the_reminder(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana. Quem vai viver na casa?")
    backdate(service, REF, CUSTOMER, 49)
    read(service, [])
    [reminder] = reminders(service)
    assert reminder["reminder"] == "2d" and reminder["reply_status"] == "pending" and not reminder["reply_text"]
    queue = service.pending()["properties"][0]
    prompt = reply_prompt(queue, [reminder["id"]])
    assert "interação: lembrete aos 2 dias" in prompt and "Quem vai viver na casa?" in prompt  # the history goes too
    assert "Lembrete sem resposta (emails marcados" in queue["instructions"]
    # 04/10: the owner's extra instructions reach the reminder too, questions included (they had been left out)
    assert "leva também as instruções extra" not in prompt
    prompt = reply_prompt(queue, [reminder["id"]], "Precisamos da disponibilidade para visitas entre 7 e 9 de outubro.")
    assert "leva também as instruções extra do proprietário, de cima, perguntas incluídas" in prompt
    assert "também os lembretes" in prompt and "entre 7 e 9 de outubro" in prompt
    assert "a não ser as que as instruções extra do proprietário pedirem" in queue["instructions"]


def test_no_reminder_for_a_customer_with_a_visit_booked(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    agenda = load_visits(service.folder, REF)
    agenda["slots"].append({"at": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d 17:00"),
                            "customer": CUSTOMER, "name": "Ana Exemplo"})
    save_visits(service.folder, REF, agenda)
    backdate(service, REF, CUSTOMER, 49)
    read(service, [])
    assert reminders(service) == []


def three_unanswered(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    for text in ("Ainda tem interesse?", "Continua à procura?"):
        draft_and_send(service, service.write_more(REF, CUSTOMER, text=text)["id"], text)


def test_three_unanswered_make_a_customer_absent_and_four_inactive_until_they_write(service):
    # 06/10, the owner's rule: the 3rd email of ours 48 hours unanswered → «ausente» (only marked, still in the rounds);
    # the 4th two working days unanswered → «inativo» (out of them); their next email brings them back
    three_unanswered(service)
    data = service.load(REF)
    now = datetime.now(timezone.utc)
    assert service.mark_inactive(REF, data, now + timedelta(hours=47)) == 0  # too soon
    assert service.mark_inactive(REF, data, now + timedelta(hours=49)) == 1
    conversation = data["conversations"][CUSTOMER]
    assert conversation["absent"]["reason"] == "3 emails nossos sem resposta" and "inactive" not in conversation
    service.save(data, REF)
    assert [c["email"] for c in service.visit_candidates()["customers"]] == [CUSTOMER]  # still in the rounds
    assert [(c["absent"], c["inactive"]) for c in service.contacts()["contacts"]] == [(True, False)]
    assert service.mark_inactive(REF, data, now + timedelta(days=30)) == 0  # three: never inactive

    draft_and_send(service, service.write_more(REF, CUSTOMER, text="Última tentativa.")["id"], "Última tentativa.")
    data = service.load(REF)
    assert service.mark_inactive(REF, data, now + timedelta(hours=12)) == 0
    assert service.mark_inactive(REF, data, now + timedelta(days=7)) == 1  # two working days, whatever the weekend
    service.save(data, REF)
    assert service.visit_candidates()["customers"] == []  # out of the rounds and the files
    assert [(c["absent"], c["inactive"]) for c in service.contacts()["contacts"]] == [(False, True)]

    read(service, [follow_up("c2", 1, "Desculpe a demora, ainda tenho interesse.", service)])
    conversation = service.load(REF)["conversations"][CUSTOMER]
    assert "inactive" not in conversation and "absent" not in conversation  # wrote again: active again
    assert [c["email"] for c in service.visit_candidates()["customers"]] == [CUSTOMER]


def test_an_email_of_ours_waiting_does_not_stop_the_count(service):
    # 06/10: a customer with one email and four of ours unanswered was never counted: our round proposal waited in the queue
    three_unanswered(service)
    service.write_more(REF, CUSTOMER, text="Mais uma.")  # prepared, not sent
    data = service.load(REF)
    assert service.mark_inactive(REF, data, datetime.now(timezone.utc) + timedelta(hours=49)) == 1
    assert data["conversations"][CUSTOMER]["absent"]


def test_working_days_skip_weekends_and_national_holidays():
    from backend.rules import after_workdays, easter, is_workday
    from datetime import date
    assert easter(2026) == date(2026, 4, 5) and not is_workday(date(2026, 4, 3))  # Good Friday
    assert not is_workday(date(2026, 10, 5)) and is_workday(date(2026, 10, 6))  # Implantação da República
    friday = datetime(2026, 10, 9, 15, 0).astimezone()
    assert after_workdays(friday, 2).date() == date(2026, 10, 13)  # Monday and Tuesday
    sunday = datetime(2026, 10, 4, 15, 0).astimezone()
    assert after_workdays(sunday, 2).date() == date(2026, 10, 7)  # not the 5th (a holiday): the 6th and the 7th


def test_an_inactive_property_does_not_wake_its_customers(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    data = service.load(REF)
    data["conversations"][CUSTOMER]["inactive"] = {"at": "2026-01-01T00:00:00+00:00", "reason": "teste"}
    service.save(data, REF)
    service.set_property_active(REF, False)
    read(service, [follow_up("c2", 1, "Ainda está disponível?", service)])
    conversation = service.load(REF)["conversations"][CUSTOMER]
    assert conversation["inactive"] and len(service.pending()["properties"][0]["emails"]) == 1  # the email still comes in


def test_a_no_show_gets_a_draft_that_blames_no_one(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    today = datetime.now().strftime("%Y-%m-%d")
    agenda = load_visits(service.folder, REF)
    agenda["slots"].append({"at": f"{today} 00:00", "customer": CUSTOMER, "name": "Ana Exemplo"})
    save_visits(service.folder, REF, agenda)
    service.check_visit(REF, CUSTOMER, False)
    service.check_visit(REF, CUSTOMER, False)  # checked again: still one draft
    [missed] = [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "visit_missed"]
    assert missed["visit_missed"] == {"at": f"{today} 00:00"} and missed["reply_status"] == "pending"
    queue = service.pending()["properties"][0]
    prompt = reply_prompt(queue, [missed["id"]])
    assert "interação: visita falhada" in prompt and "não aconteceu" in prompt
    assert "sem culpar ninguém" in queue["instructions"]
    service.check_visit(REF, CUSTOMER, True)  # corrected: they did come, the draft goes away
    assert [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "visit_missed"] == []


def test_no_reminder_after_six_days_of_silence(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    backdate(service, REF, CUSTOMER, 24 * 20)  # an old conversation from the backlog
    read(service, [])
    assert reminders(service) == []


def test_no_reminder_after_a_visit_proposal(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    data = service.load(REF)
    data["conversations"][CUSTOMER]["stage"] = 3  # proposed in a round whose window is gone
    service.save(data, REF)
    backdate(service, REF, CUSTOMER, 50)
    read(service, [])
    assert reminders(service) == []
