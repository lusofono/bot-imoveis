import json
from datetime import datetime, timedelta, timezone
import pytest
from test_properties import draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)


def log_event(service, days_ago, **fields):
    logs = service.folder / "logs"
    logs.mkdir(exist_ok=True)
    at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    with (logs / "events.jsonl").open("a") as stream:
        stream.write(json.dumps({"at": at, **fields}) + "\n")


def sent_event(service, days_ago, **fields):
    log_event(service, days_ago, event="send", status="sent", **fields)


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


def test_openai_usage_splits_into_period_and_all_time(service):
    log_event(service, 20, event="openai_usage", model="gpt-4o", prompt_tokens=1000, completion_tokens=200, cost_usd=0.0045)
    log_event(service, 1, event="openai_usage", model="gpt-4o", prompt_tokens=500, completion_tokens=100, cost_usd=0.0024)
    usage = service.metrics(14)["openai_usage"]
    assert usage["period"] == {"calls": 1, "prompt_tokens": 500, "completion_tokens": 100, "cost_usd": 0.0024}
    assert usage["all_time"] == {"calls": 2, "prompt_tokens": 1500, "completion_tokens": 300, "cost_usd": 0.0069}


def test_no_openai_usage_yet_is_all_zeros(service):
    usage = service.metrics()["openai_usage"]
    assert usage["period"] == usage["all_time"] == {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0}


def test_each_property_gets_its_own_numbers_and_old_events_are_attributed(service):
    from test_properties import REF
    from backend.store import save_json
    read(service, [lead("1")])
    draft_and_send(service, "1")  # logged with its property since 24/09
    profile = json.loads((service.folder / "properties" / REF / "profile.json").read_text(encoding="utf-8"))
    profile["property"]["reference"] = profile["match"]["subject_property_reference_equals"] = "OUTRO"
    save_json(service.folder / "properties" / "OUTRO" / "profile.json", profile)
    # An older send, logged before events carried a property: found by the IDs that queue kept.
    queue = service.load("OUTRO")
    queue["replied_message_ids"].append("antigo")
    service.save(queue, "OUTRO")
    sent_event(service, 0, message_id="antigo", waited_hours=10.0)
    log_event(service, 1, event="openai_usage", reference=REF, prompt_tokens=100, completion_tokens=10, cost_usd=0.001)
    log_event(service, 1, event="openai_usage", prompt_tokens=50, completion_tokens=5, cost_usd=0.0005)  # before 24/09

    metrics = service.metrics(14)
    mine, other = (next(p for p in metrics["properties"] if p["property_ref"] == ref) for ref in (REF, "OUTRO"))
    assert sum(day["sent"] for day in mine["by_day"]) == 1 and sum(day["requests"] for day in mine["by_day"]) == 1
    assert sum(day["sent"] for day in other["by_day"]) == 1 and other["reply_hours"] == 10.0
    assert mine["openai_usage"]["all_time"]["calls"] == 1 and other["openai_usage"]["all_time"]["calls"] == 0
    assert metrics["openai_usage"]["unattributed"]["calls"] == 1 and metrics["openai_usage"]["all_time"]["calls"] == 2
    assert mine["clients"]["ok"] == 1 and mine["ignored"] == {"black": 0, "grey": 0}


def test_each_property_sets_its_own_reply_time_limit_the_temperature_dials_top(service):
    from test_properties import REF
    read(service, [lead("1")])
    [mine] = service.metrics()["properties"]
    assert mine["reply_hours_max"] == 24  # until the owner sets one
    assert service.save_panel(REF, "12")["reply_hours_max"] == 12
    assert service.metrics()["properties"][0]["reply_hours_max"] == 12
    assert service.save_panel(REF, 36.5)["reply_hours_max"] == 36.5
    events = [json.loads(line) for line in (service.folder / "logs" / "events.jsonl").read_text().splitlines()]
    assert events[-1] == {**events[-1], "event": "panel_saved", "reference": REF, "reply_hours_max": 36.5}
    for bad in (0, 721, "doze", float("nan")):
        with pytest.raises(ValueError, match="tempo máximo"):
            service.save_panel(REF, bad)
    with pytest.raises(ValueError, match="Indica o que guardar"):
        service.save_panel(REF)
    for ref in ("OUTRO", "../fora", None):
        with pytest.raises(ValueError):
            service.save_panel(ref, 12)
    assert not (service.folder / "fora").exists() and not (service.folder / "painel.json").exists()
    # A hand-edited file with nonsense in it reads as the default, never as a broken dial.
    (service.folder / "properties" / REF / "painel.json").write_text('{"reply_hours_max": "muito"}')
    assert service.metrics()["properties"][0]["reply_hours_max"] == 24


def test_the_visits_petrol_counts_one_round_trip_per_visit_day_already_begun(service):
    from test_properties import REF
    from backend.store import save_visits
    read(service, [lead("1")])
    assert service.metrics()["properties"][0]["petrol"]["litres"] is None  # no distance yet: unknown, not zero
    assert service.save_panel(REF, distance_km=18) == {"reply_hours_max": 24, "distance_km": 18, "l_per_100km": 7.0}
    day = lambda offset: (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")
    save_visits(service.folder, REF, {"windows": [], "closed_at": None, "slots": [
        {"at": f"{day(-2)} 17:00", "customer": "a@example.com"}, {"at": f"{day(-2)} 17:30", "customer": "b@example.com"},
        {"at": f"{day(-5)} 10:00", "customer": "c@example.com"}, {"at": f"{day(3)} 18:00", "customer": "d@example.com"}]})
    # Two days already gone (two visits on one of them: still one trip), one ahead: 2 × 2 × 18 km at 7 L/100 km.
    assert service.metrics()["properties"][0]["petrol"] == {"distance_km": 18, "l_per_100km": 7.0, "trips": 2,
                                                            "planned_trips": 1, "km": 72, "litres": 5.0, "planned_litres": 2.5}
    assert service.save_panel(REF, l_per_100km="5,5".replace(",", "."))["l_per_100km"] == 5.5
    for bad in ({"distance_km": -1}, {"distance_km": 1001}, {"l_per_100km": 0.5}, {"l_per_100km": "muito"}):
        with pytest.raises(ValueError, match="distância|consumo"):
            service.save_panel(REF, **bad)


def test_each_property_spends_only_its_own_tank_starting_from_the_old_shared_one(service):
    from test_properties import REF
    from backend.store import save_json
    read(service, [lead("1")])
    profile = json.loads((service.folder / "properties" / REF / "profile.json").read_text(encoding="utf-8"))
    profile["property"]["reference"] = profile["match"]["subject_property_reference_equals"] = "OUTRO"
    save_json(service.folder / "properties" / "OUTRO" / "profile.json", profile)
    # The one shared tank of before (with the rate it had then, now ignored): where every property starts.
    filled = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    save_json(service.folder / "api_fuel.json", {"capacity_eur": 5, "usd_to_eur": 0.9, "filled_at": filled})
    log_event(service, 0, event="openai_usage", reference=REF, cost_usd=1.5)
    log_event(service, 0, event="openai_usage", reference="OUTRO", cost_usd=0.5)
    assert (service.api_fuel(REF)["remaining_eur"], service.api_fuel("OUTRO")["remaining_eur"]) == (3.5, 4.5)
    assert service.fill_fuel("OUTRO", 2)["remaining_eur"] == 2  # its own tank from now on; REF keeps the old one
    log_event(service, 0, event="openai_usage", reference="OUTRO", cost_usd=0.25)
    tanks = {item["property_ref"]: item["api_fuel"]["remaining_eur"] for item in service.metrics()["properties"]}
    assert tanks == {REF: 3.5, "OUTRO": 1.75}
    with pytest.raises(ValueError, match="Indica o imóvel"):
        service.fill_fuel(None, 2)  # with two properties, a fill must say which
