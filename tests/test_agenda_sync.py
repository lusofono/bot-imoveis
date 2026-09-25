"""«Atualizar agenda»: the API reads the conversations and updates the agenda by itself (the owner's choice)."""
import json
from datetime import date, timedelta
from unittest.mock import patch
from backend.store import load_visits, save_visits
from test_properties import REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

DAY = (date.today() + timedelta(days=2)).isoformat()
USAGE = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}


def customers(service, *emails):
    for number, email in enumerate(emails, 1):
        read(service, [lead(str(number), reply_to=(email,), body_email=email)])
        draft_and_send(service, str(number), "Olá.")


def sync(service, answer):
    with patch("backend.service.has_openai_api_key", return_value=True), \
            patch("backend.service.openai_api_key", return_value="sk-test"), \
            patch("backend.service.complete", return_value=(json.dumps(answer), USAGE)) as call:
        return service.sync_agenda(), call


def test_what_we_confirmed_is_booked_and_what_the_customer_accepted_shows_orange(service):
    customers(service, "a@example.com", "b@example.com", "c@example.com")
    result, call = sync(service, {"clientes": [
        {"id": "c1", "estado": "confirmada", "hora": f"{DAY} 15:00", "prova": "Fica confirmado às 15:00."},
        {"id": "c2", "estado": "aceite", "hora": f"{DAY} 16:00", "prova": "Posso às 16h."},
        {"id": "c3", "estado": "nenhuma", "hora": None, "prova": ""},
        {"id": "c9", "estado": "confirmada", "hora": f"{DAY} 17:00", "prova": "inventado"},  # unknown id
    ]})
    [prop] = result["properties"]
    assert (prop["asked"], prop["confirmed"], prop["accepted"]) == (3, 1, 1)
    prompt = call.call_args.args[2]
    assert "a@example.com" not in prompt and "id: c1" in prompt  # addresses never go to the model
    agenda = load_visits(service.folder, REF)
    assert [(slot["at"], slot["customer"], slot["source"]) for slot in agenda["slots"]] == [(f"{DAY} 15:00", "a@example.com", "api")]
    visits = next(p for p in service.settings()["properties"] if p["reference"] == REF)["visits"]
    assert [(visit["at"], visit["customer"]) for visit in visits["accepted"]] == [(f"{DAY} 16:00", "b@example.com")]

    # Next time: B's time is now confirmed; A's booking still holds; C still nothing.
    result, call = sync(service, {"clientes": [
        {"id": "c1", "estado": "confirmada", "hora": f"{DAY} 15:00", "prova": "Confirmado."},
        {"id": "c2", "estado": "confirmada", "hora": f"{DAY} 16:00", "prova": "Confirmado às 16:00."},
        {"id": "c3", "estado": "nenhuma", "hora": None, "prova": ""}]})
    assert result["properties"][0]["asked"] == 3  # the booked are asked again: a time may have changed
    assert f"na agenda agora: {DAY} 15:00" in call.call_args.args[2]
    agenda = load_visits(service.folder, REF)
    assert sorted((slot["customer"], slot["at"]) for slot in agenda["slots"]) == [
        ("a@example.com", f"{DAY} 15:00"), ("b@example.com", f"{DAY} 16:00")]
    visits = next(p for p in service.settings()["properties"] if p["reference"] == REF)["visits"]
    assert visits["accepted"] == []


def test_the_latest_email_wins_a_moved_time_and_our_own_offer_still_unanswered(service):
    # The page booked A at 12:00 and B at 14:00; later, in Gmail, the owner moved A to 13:00 and offered B 14:30.
    customers(service, "a@example.com", "b@example.com")
    agenda = load_visits(service.folder, REF)
    agenda["slots"] += [{"at": f"{DAY} 12:00", "customer": "a@example.com"}, {"at": f"{DAY} 14:00", "customer": "b@example.com"}]
    save_visits(service.folder, REF, agenda)
    result, _ = sync(service, {"clientes": [
        {"id": "c1", "estado": "confirmada", "hora": f"{DAY} 13:00", "prova": "Fica então marcado às 13:00."},
        {"id": "c2", "estado": "proposta", "hora": f"{DAY} 14:30", "prova": "It's available 14:30 tomorrow."}]})
    prop = result["properties"][0]
    assert (prop["moved"], prop["offered"], prop["unbooked"]) == (1, 1, 1)
    [slot] = load_visits(service.folder, REF)["slots"]
    assert (slot["customer"], slot["at"], slot["previous"], slot["source"]) == ("a@example.com", f"{DAY} 13:00", f"{DAY} 12:00", "api")
    visits = next(p for p in service.settings()["properties"] if p["reference"] == REF)["visits"]
    assert [(v["customer"], v["at"], v["replaces"]) for v in visits["offered"]] == [("b@example.com", f"{DAY} 14:30", f"{DAY} 14:00")]
    # A vague answer about someone booked never unbooks them.
    sync(service, {"clientes": [{"id": "c1", "estado": "nenhuma", "hora": None, "prova": ""}]})
    assert [slot["at"] for slot in load_visits(service.folder, REF)["slots"]] == [f"{DAY} 13:00"]


def test_a_day_in_the_past_or_a_made_up_time_never_reaches_the_agenda(service):
    customers(service, "a@example.com", "b@example.com")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    sync(service, {"clientes": [{"id": "c1", "estado": "confirmada", "hora": f"{yesterday} 10:00", "prova": "x"},
                                {"id": "c2", "estado": "aceite", "hora": "sexta à tarde", "prova": "x"}]})
    assert load_visits(service.folder, REF)["slots"] == []
    assert next(p for p in service.settings()["properties"] if p["reference"] == REF)["visits"]["accepted"] == []


def test_without_a_key_it_says_so_and_with_an_empty_tank_the_property_is_skipped(service):
    customers(service, "a@example.com")
    with patch("backend.service.has_openai_api_key", return_value=False):
        try:
            service.sync_agenda()
            raise AssertionError("expected an error")
        except ValueError as error:
            assert "chave da OpenAI" in str(error)
    with patch.object(type(service), "api_fuel", return_value={"empty": True}):
        result, call = sync(service, {"clientes": []})
    assert result["properties"][0]["skipped"] and call.call_count == 0
