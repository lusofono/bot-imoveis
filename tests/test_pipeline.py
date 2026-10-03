"""The customers by step (27/09), in the table above the emails: one column each, the furthest they got."""
import json
from datetime import datetime, timedelta, timezone
from backend.service import ficha_update
from backend.store import save_json, save_visits
from test_properties import CUSTOMER, REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

OTHER = "bruno.exemplo@example.com"


def columns(service):
    return {customer["email"]: (customer["column"], customer["waiting"])
            for customer in service.pending()["properties"][0]["pipeline"]}


def change(service, email, **fields):
    data = service.load(REF)
    data["conversations"][email].update(fields)
    service.save(data, REF)


def test_each_customer_sits_in_the_column_of_the_furthest_step_they_got_to(service):
    read(service, [lead("1")])
    # Not answered yet: the first contact, waiting for us.
    assert columns(service) == {CUSTOMER: ("contacto", True)}
    draft_and_send(service, "1")
    assert columns(service) == {CUSTOMER: ("qualificacao", False)}
    # Our email unanswered for 3 days or more, whatever the step: «Sem resposta».
    change(service, CUSTOMER, last_sent_at=(datetime.now(timezone.utc) - timedelta(days=3, minutes=1)).isoformat())
    assert columns(service)[CUSTOMER] == ("sem_resposta", False)
    # They write again: back in their step, waiting for us.
    read(service, [dict(lead("2"), thread_id="t1")])
    assert columns(service)[CUSTOMER] == ("qualificacao", True)
    # 29/09: by phase, not by how many emails: however many questions it took, still «Em qualificação»...
    change(service, CUSTOMER, stage=5)
    assert columns(service)[CUSTOMER] == ("qualificacao", True)
    # ...«Pronto para visita» once their file is complete...
    change(service, CUSTOMER, ficha=ficha_update(None, COMPLETE))
    assert columns(service)[CUSTOMER] == ("pronto", True)
    # ...«Proposta de visita» once a visit is proposed to them, and «Hora por confirmar» once they accept a time.
    change(service, CUSTOMER, visit_proposed=True)
    assert columns(service)[CUSTOMER] == ("proposta", True)
    change(service, CUSTOMER, visit_accepted={"at": "2026-10-01 18:00", "evidence": "Pode ser às 18h."})
    assert columns(service)[CUSTOMER] == ("por_confirmar", True)

    # A visit on the agenda, then attended, then on the short list; declining it puts them aside.
    save_visits(service.folder, REF, {"windows": [], "slots": [{"at": "2026-10-01 18:00", "customer": CUSTOMER}]})
    assert columns(service)[CUSTOMER][0] == "marcada"
    save_visits(service.folder, REF, {"windows": [], "slots": [
        {"at": "2026-10-01 18:00", "customer": CUSTOMER, "check": {"attended": True}}]})
    assert columns(service)[CUSTOMER][0] == "visitou"
    change(service, CUSTOMER, selection={"status": "shortlist"})
    assert columns(service)[CUSTOMER][0] == "shortlist"
    change(service, CUSTOMER, visit="nao_quer")
    assert columns(service)[CUSTOMER][0] == "desistiu"
    # The greylist and the blacklist go under the table, each on its own line.
    change(service, CUSTOMER, ignored=True, ignored_kind="grey", ignored_reason="Já arrendou outra casa.")
    assert columns(service)[CUSTOMER][0] == "greylist"
    assert service.pending()["properties"][0]["pipeline"][0]["reason"] == "Já arrendou outra casa."  # shown after the name
    change(service, CUSTOMER, ignored_kind="black")
    assert columns(service)[CUSTOMER][0] == "blacklist"


def dots(service):
    return {customer["email"]: customer["dots"] for customer in service.pending()["properties"][0]["pipeline"]}


COMPLETE = {"trabalho": "Engenheira", "agregado": "Casal", "datas": "Um ano", "disponibilidade": "Fins de tarde"}


def test_the_dots_say_what_needs_doing_with_the_hours_set_in_the_voice(service):
    now = datetime.now(timezone.utc)
    read(service, [dict(lead("1"), date=(now - timedelta(hours=49)).isoformat())])
    assert dots(service) == {CUSTOMER: ["late"]}  # waiting for us more than 48 h (red, on our half)
    draft_and_send(service, "1")
    assert dots(service) == {CUSTOMER: ["red", "ok"]}  # never answered us; we are up to date
    change(service, CUSTOMER, ficha={**COMPLETE, "at": now.isoformat(), "complete_at": now.isoformat()})
    assert dots(service) == {CUSTOMER: ["green", "ok"]}
    old = (now - timedelta(hours=97)).isoformat()
    change(service, CUSTOMER, ficha={**COMPLETE, "at": old, "complete_at": old})
    assert dots(service) == {CUSTOMER: ["green", "blue"]}  # they gave all; we: complete for 4 days and no visit date
    # The hours come from Voz e estilo.
    voice = json.loads((service.folder / "voice.json").read_text(encoding="utf-8"))
    voice["style"]["alerts"] = {"our_turn_hours": 24, "no_visit_hours": 120}
    save_json(service.folder / "voice.json", voice)
    assert dots(service) == {CUSTOMER: ["green", "ok"]}
    assert service.settings()["voice"]["alerts"] == {"our_turn_hours": 24, "no_visit_hours": 120}
    # A visit proposed: no blue, whatever the time.
    voice["style"]["alerts"] = {"our_turn_hours": 24, "no_visit_hours": 96}
    save_json(service.folder / "voice.json", voice)
    change(service, CUSTOMER, visit_offered={"at": now.isoformat()})
    assert dots(service) == {CUSTOMER: ["green", "ok"]}


def test_a_file_remembers_when_it_became_complete():
    first = ficha_update(None, {"trabalho": "Engenheira"})
    assert "complete_at" not in first
    done = ficha_update(first, COMPLETE)
    assert done["complete_at"] == done["at"]
    later = ficha_update({**done, "complete_at": "2026-09-01T10:00:00+00:00"}, {"animais": "Um gato"})
    assert later["complete_at"] == "2026-09-01T10:00:00+00:00" and later["animais"] == "Um gato"


def test_the_table_has_names_and_the_newest_first(service):
    read(service, [dict(lead("1"), date="2026-09-20T10:00:00+00:00"),
                   dict(lead("2", reply_to=(OTHER,)), date="2026-09-25T10:00:00+00:00")])
    pipeline = service.pending()["properties"][0]["pipeline"]
    assert [customer["email"] for customer in pipeline] == [OTHER, CUSTOMER]
    assert pipeline[1]["name"] == "Ana Exemplo" and pipeline[1]["last_at"].startswith("2026-09-20")


def test_a_customer_writing_with_a_visit_booked_or_after_it_gets_its_own_prompt(service):
    # 27/09: they went as a plain «5.ª» or later, which has no prompt.
    from datetime import date
    from backend.ai import reply_prompt
    read(service, [lead("1")])
    draft_and_send(service, "1")
    follow = {"gmail_message_id": "f1", "thread_id": "t1", "message_id": "<f1@mail.example>", "date": NOW_ISO(),
              "from": [{"name": "Ana Exemplo", "email": CUSTOMER}], "subject": "Re: Nova mensagem",
              "body_text": "A garagem dá para dois carros?"}
    day = (date.today() + timedelta(days=2)).isoformat()
    save_visits(service.folder, REF, {"windows": [], "slots": [{"at": day + " 18:00", "customer": CUSTOMER}]})
    read(service, [follow])
    queue = service.pending()["properties"][0]
    [email] = [item for item in queue["emails"] if item["id"] == "f1"]
    assert (email["phase"], email["booked_at"]) == ("booked", day + " 18:00")
    prompt = reply_prompt(queue, ["f1"])
    assert "interação: visita marcada" in prompt and "Visita marcada para" in prompt and "Cliente com visita marcada" in prompt
    # After the visit: «já visitou».
    change(service, CUSTOMER, visit_check={"at": day + " 18:00", "attended": True})
    queue = service.pending()["properties"][0]
    [email] = [item for item in queue["emails"] if item["id"] == "f1"]
    assert email["phase"] == "visited" and "interação: já visitou" in reply_prompt(queue, ["f1"])


def NOW_ISO():
    return datetime.now(timezone.utc).isoformat()



def halves(service):
    return {customer["email"]: (customer["them"], customer["us"]) for customer in service.pending()["properties"][0]["pipeline"]}


def test_one_dot_in_two_halves_what_they_gave_and_what_we_have_to_do(service):
    read(service, [lead("1")])
    assert halves(service) == {CUSTOMER: (None, "amber")}  # a new request: nothing asked yet, and ours to answer soon
    draft_and_send(service, "1")
    assert halves(service) == {CUSTOMER: ("red", "ok")}  # asked, nothing given yet; we are up to date
    change(service, CUSTOMER, ficha={"trabalho": "Engenheira"},
           history=[{"who": "nos", "text": "Olá."}, {"who": "cliente", "text": "Sou engenheira."}])
    assert halves(service) == {CUSTOMER: ("yellow", "ok")}  # part of the file
    change(service, CUSTOMER, visit="nao_quer")
    assert halves(service)[CUSTOMER] == ("black", "black")  # declined: a dot too, all black



def test_an_almost_empty_addition_goes_when_the_customer_writes_again_and_a_gmail_answer_is_greyed(service):
    read(service, [lead("1")])
    draft_and_send(service, "1")
    service.write_more(REF, CUSTOMER)  # «Escrever mais»: an «acrescento» in their conversation
    queue = service.load(REF)
    [addition] = [item for item in queue["emails"] if item.get("kind") == "addition"]
    addition["reply_text"] = "pdf"
    service.save(queue, REF)
    sent = service.load(REF)["conversations"][CUSTOMER]["sent_message_ids"][-1]
    read(service, [{"gmail_message_id": "2", "from": [{"email": CUSTOMER}], "in_reply_to": sent,
                    "subject": "Re: resposta", "body_text": "Tenho uma pergunta."}])
    kinds = [item.get("kind") for item in service.pending()["properties"][0]["emails"]]
    assert kinds == ["follow_up"]  # the «pdf» addition went, their new email stays
    queue = service.load(REF)
    queue["emails"][0]["answered_directly"] = {"at": "2026-09-30T17:19:41+00:00", "interaction": 2}
    service.save(queue, REF)
    assert service.pending()["properties"][0]["emails"][0]["answered_direct"] is True
