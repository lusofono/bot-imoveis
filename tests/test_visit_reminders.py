"""Visit reminders: one the day before and one on the day, drafted by the program, written by the assistant."""
from datetime import date, datetime, timedelta
from unittest.mock import patch
from backend.ai import reply_prompt
from test_properties import REF, SMTP, draft_and_send, read, service  # noqa: F401 (service is a fixture)
from test_visits import DAY, customer

EMAIL = "a@example.com"


def booked(service, at=f"{DAY} 17:30"):
    """A customer with a visit booked (by default tomorrow at 17:30), through a round like in real use."""
    read(service, [customer("1", EMAIL)])
    draft_and_send(service, "1", "Olá.")
    service.propose_visits(REF, at[:10], "17:00", "19:00", [EMAIL])
    [proposal] = service.pending()["properties"][0]["emails"]
    revision = service.pending()["properties"][0]["revision"]
    service.drafts([{"id": proposal["id"], "reply_text": "Fica marcado."}], revision, REF,
                   [{"id": proposal["id"], "visit_slot": at}])
    send(service, proposal["id"])


def send(service, key):
    preview = service.preview([key], REF)
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        return service.send(preview["preview_token"], True, REF)


def reminders(service):
    return [e for e in service.pending()["properties"][0]["emails"] if e["kind"] == "visit_reminder"]


def test_the_day_before_a_reminder_is_drafted_once_and_written_by_the_assistant(service):
    booked(service)
    read(service, [])
    read(service, [])  # a second read the same day adds nothing
    [reminder] = reminders(service)
    assert reminder["visit_reminder"] == {"at": f"{DAY} 17:30", "when": "vespera"} and reminder["reply_status"] == "pending"
    assert any("Ficha incompleta" in warning for warning in reminder["warnings"])
    queue = service.pending()["properties"][0]
    prompt = reply_prompt(queue, [reminder["id"]])
    assert "interação: lembrete de visita" in prompt and "é o lembrete da visita marcada para" in prompt
    assert "amanhã" in prompt and "No fim do lembrete, lembra" in prompt
    assert "Lembrete de visita (emails marcados «lembrete de visita»): Lembra o cliente" in queue["instructions"]

    before = service.load(REF)["conversations"][EMAIL]
    draft_and_send(service, reminder["id"], "Lembramos a sua visita amanhã às 17:30.")
    after = service.load(REF)["conversations"][EMAIL]
    # Not an interaction: the step and the clock of the 2/4-day reminders stay as they were.
    assert (after["stage"], after["last_sent_at"]) == (before["stage"], before["last_sent_at"])
    assert after["visit_reminders_sent"] == [f"{DAY} 17:30|vespera"]
    read(service, [])
    assert reminders(service) == []  # sent once, never again


def test_on_the_day_the_unsent_reminder_of_the_day_before_is_replaced(service):
    booked(service)
    read(service, [])
    [eve] = reminders(service)
    data = service.load(REF)
    visit_day = date.fromisoformat(DAY)
    assert service.schedule_visit_reminders(REF, data, datetime.combine(visit_day, datetime.min.time()) + timedelta(hours=8)) == 1
    [day] = [item for item in data["emails"] if item["kind"] == "visit_reminder"]
    assert day["visit_reminder"]["when"] == "dia" and day["id"] != eve["id"]
    # After the visit's time: nothing more for that day.
    assert service.schedule_visit_reminders(REF, data, datetime.combine(visit_day, datetime.min.time()) + timedelta(hours=18)) == 0


def test_no_reminder_when_dismissed_ignored_or_asked_for_another_date(service):
    booked(service)
    read(service, [])
    [reminder] = reminders(service)
    service.dismiss([reminder["id"]], service.pending()["properties"][0]["revision"], REF)
    read(service, [])
    assert reminders(service) == []  # the owner said no: it does not come back
    data = service.load(REF)
    data["dismissed_message_ids"] = []
    data["conversations"][EMAIL]["visit"] = "outra_data"
    assert service.schedule_visit_reminders(REF, data) == 0
    data["conversations"][EMAIL]["visit"] = None
    data["conversations"][EMAIL]["ignored"] = True
    assert service.schedule_visit_reminders(REF, data) == 0
