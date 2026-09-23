import json
from datetime import datetime, timedelta, timezone
import pytest
from test_properties import draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)


def sent_event(service, days_ago, **fields):
    logs = service.folder / "logs"
    logs.mkdir(exist_ok=True)
    at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    with (logs / "events.jsonl").open("a") as stream:
        stream.write(json.dumps({"at": at, "event": "send", "status": "sent", **fields}) + "\n")


def requests_by_day(service, days=14):
    return {day["day"]: day["requests"] for day in service.metrics(days)["by_day"] if day["requests"]}


def test_a_request_still_counts_after_it_is_answered_and_leaves_the_queue(service):
    read(service, [lead("1")])
    today = service.metrics()["by_day"][-1]["day"]
    assert requests_by_day(service) == {today: 1}
    draft_and_send(service, "1")
    assert service.metrics()["totals"]["pending"] == 0
    assert requests_by_day(service) == {today: 1}  # from the day READ logged, not from the queue


def test_older_answered_requests_are_dated_by_the_hours_the_customer_waited(service):
    # Sent today after a 48-hour wait: that email arrived two days ago. A reminder answers nobody.
    sent_event(service, 0, message_id="old", waited_hours=48.0)
    sent_event(service, 0, message_id="lembrete", waited_hours=30.0, kind="reminder")
    two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
    assert requests_by_day(service) == {two_days_ago: 1}
    assert service.metrics()["reply_hours"] == 48.0


@pytest.mark.parametrize("days, bars, step", [(3, 3, 1), (7, 7, 1), (14, 14, 1), (30, 30, 1), (90, 13, 7)])
def test_each_period_has_readable_bars(service, days, bars, step):
    metrics = service.metrics(days)
    assert (len(metrics["by_day"]), metrics["bucket_days"], metrics["period_days"]) == (bars, step, days)
    assert metrics["by_day"][-1]["day"] <= datetime.now(timezone.utc).date().isoformat()


def test_a_send_counts_only_inside_the_chosen_period(service):
    sent_event(service, 10)
    assert sum(day["sent"] for day in service.metrics(7)["by_day"]) == 0
    assert sum(day["sent"] for day in service.metrics(14)["by_day"]) == 1
    # Three months: the same send lands in exactly one weekly bar.
    assert sum(day["sent"] for day in service.metrics(90)["by_day"]) == 1


def test_an_unknown_period_is_refused(service):
    with pytest.raises(ValueError, match="Período"):
        service.metrics(10)
