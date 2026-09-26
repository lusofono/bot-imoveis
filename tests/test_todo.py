"""«A fazer» in the dashboard: worked out from the data, most urgent first, first names only."""
import json
from datetime import date, timedelta
from backend.store import load_visits, save_visits
from test_properties import REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)
from test_visit_reminders import EMAIL, booked
from test_visits import DAY, customer


def kinds(service):
    return {task["kind"]: task for task in service.todo()["tasks"]}


def test_the_queue_the_agenda_and_the_setup_become_tasks_that_go_away_when_done(service):
    tasks = kinds(service)
    assert set(tasks) == {"setup"} and tasks["setup"]["tab"] == "voice"
    assert "lembretes de 2 e 4 dias" in tasks["setup"]["text"]

    read(service, [lead("1")])
    task = kinds(service)["reply"]
    assert (task["tab"], task["property_ref"], task["count"], task["names"]) == ("replies", REF, 1, ["Ana"])
    revision = service.pending()["properties"][0]["revision"]
    service.drafts([{"id": "1", "reply_text": "Olá."}], revision, REF)
    assert "reply" not in kinds(service) and kinds(service)["draft"]["count"] == 1

    draft_and_send(service, "1", "Olá.")
    assert {"reply", "draft"}.isdisjoint(kinds(service))
    # The only thing that ever leaves this call about a customer is a first name.
    assert "@" not in json.dumps(service.todo())


def test_visit_tasks_reminders_checks_and_thanks(service):
    booked(service)
    read(service, [])
    tasks = service.todo()["tasks"]
    assert tasks[0]["kind"] == "visit_reminder"  # the most urgent first: it goes out to a customer today
    service.dismiss([item["id"] for item in service.pending()["properties"][0]["emails"]],
                    service.pending()["properties"][0]["revision"], REF)

    agenda = load_visits(service.folder, REF)  # the visit happened yesterday
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    agenda["slots"][0]["at"] = f"{yesterday} 10:00"
    save_visits(service.folder, REF, agenda)
    task = kinds(service)["check"]
    assert (task["tab"], task["property_ref"], task["count"]) == ("agenda", REF, 1)

    service.check_visit(REF, EMAIL, True, at=f"{yesterday} 10:00")
    tasks = kinds(service)
    assert "check" not in tasks and tasks["thanks"]["count"] == 1
    service.visit_thanks(REF, EMAIL)  # the thanks is now a draft in the queue: a queue task, not an agenda one
    tasks = kinds(service)
    assert "thanks" not in tasks and tasks["reply"]["count"] == 1


def test_customers_ready_for_a_round_and_the_brake(service):
    read(service, [customer("1", EMAIL)])
    draft_and_send(service, "1", "Olá.")
    data = service.load(REF)
    data["conversations"][EMAIL]["ficha"] = {"trabalho": "Professora", "agregado": "Casal", "datas": "2 anos",
                                             "disponibilidade": "Tardes", "falta_extra": []}
    service.save(data, REF)
    task = kinds(service)["ready"]
    assert (task["tab"], task["count"]) == ("properties", 1)

    data["conversations"][EMAIL]["ficha"] = {}
    data["conversations"][EMAIL]["stage"] = 4
    service.save(data, REF)
    tasks = kinds(service)
    assert "ready" not in tasks and tasks["brake"]["tab"] == "contacts"

    service.propose_visits(REF, DAY, "17:00", "19:00", [EMAIL])  # proposed: no longer a qualification task
    assert {"ready", "brake"}.isdisjoint(kinds(service))


def test_an_inactive_property_keeps_only_its_queue_tasks(service):
    read(service, [customer("1", EMAIL)])
    draft_and_send(service, "1", "Olá.")
    data = service.load(REF)
    data["conversations"][EMAIL]["ficha"] = {"trabalho": "x", "agregado": "x", "datas": "x", "disponibilidade": "x"}
    service.save(data, REF)
    service.set_property_active(REF, False)
    assert "ready" not in kinds(service)
    read(service, [lead("2")])
    assert kinds(service)["reply"]["count"] == 1
