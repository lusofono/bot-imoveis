"""The qualification (the 2nd interaction, repeated until a visit is proposed) and the customer's file it fills."""
import json
from unittest.mock import patch
from backend.ai import parse_fichas, reply_prompt, short_id
from backend.rules import clean_ficha, ficha_summary, merge_ficha
from test_merge import follow_up
from test_properties import CUSTOMER, REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (fixtures)
from test_visits import DAY, customer
from test_web import page  # noqa: F401 (fixture)


def card(service):
    [email] = service.pending()["properties"][0]["emails"]
    return email


def test_until_a_visit_is_proposed_every_email_is_the_qualification_with_a_brake(service):
    read(service, [lead("1")])
    assert card(service)["interaction"] == 1
    draft_and_send(service, "1", "Olá, Ana. Quem vai viver na casa?")
    for step, key in enumerate(("c2", "c3", "c4"), start=1):
        read(service, [follow_up(key, 1, "Mais uma resposta.", service)])
        email = card(service)
        assert email["interaction"] == 2 and not email["qualifying_limit"], step  # never the 3rd by counting
        draft_and_send(service, key, "Obrigado. Falta só um dado.")
    # The 1st reply and three questions already: the assistant stops asking and the owner is told.
    read(service, [follow_up("c5", 1, "Ainda mais uma.", service)])
    email = card(service)
    assert email["interaction"] == 2 and email["qualifying_limit"]
    assert any("três vezes" in warning for warning in email["warnings"])
    queue = service.pending()["properties"][0]
    assert "não voltes a perguntar" in reply_prompt(queue, [email["id"]])
    assert "A 2.ª interação é a qualificação e repete-se" in queue["instructions"]

    # Once a visit was proposed, the count goes on as before.
    data = service.load(REF)
    data["conversations"][CUSTOMER]["visit_proposed"] = True
    service.save(data, REF)
    email = card(service)
    assert email["interaction"] == 5 and not email["qualifying_limit"]


def test_the_file_is_cleaned_merged_and_summed_up():
    ficha = clean_ficha({"trabalho": "  Engenheira,   contrato sem termo ", "agregado": None, "datas": "null",
                         "disponibilidade": True, "animais": "x" * 400, "falta": ["animais", "empresa", "agregado"],
                         "outro": "ignorado"})
    assert ficha == {"trabalho": "Engenheira, contrato sem termo", "animais": "x" * 300, "falta_extra": ["empresa"]}
    merged = merge_ficha(ficha, {"agregado": "Dois adultos", "falta_extra": []})
    assert merged == {"trabalho": "Engenheira, contrato sem termo", "animais": "x" * 300, "agregado": "Dois adultos",
                      "falta_extra": []}
    assert ficha_summary(merged) == {"falta": ["datas", "disponibilidade"], "complete": False, "known": 2, "total": 4}
    assert ficha_summary(None)["falta"] == ["trabalho", "agregado", "datas", "disponibilidade"]
    assert ficha_summary({**merged, "datas": "Outubro, 2 anos", "disponibilidade": "Fins de tarde"})["complete"]


def test_the_file_comes_with_the_pasted_answer_and_shows_in_contacts(service, page):
    client, call = page
    read(service, [lead("1")])
    queue = service.pending()["properties"][0]
    assert "Ficha do cliente até agora: situação profissional e rendimentos: falta" in reply_prompt(queue, ["1"])
    answer = {"respostas": [{"id": short_id("1"), "reply_text": "Olá, Ana. Quem vai viver na casa?",
                             "ficha": {"trabalho": "Enfermeira no hospital", "agregado": None, "falta": ["animais"]}}]}
    status, pasted = call("/api/paste", {"property_ref": REF, "text": json.dumps(answer)})
    assert status == 200 and pasted["fichas"] == 1
    # A new customer has no conversation yet: the file waits on their email, and follows it when it is sent.
    assert card(service)["ficha_summary"] == {"falta": ["agregado", "datas", "disponibilidade", "animais"],
                                              "complete": False, "known": 1, "total": 4}
    SMTP.sent = []
    preview = service.preview(["1"])
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.send(preview["preview_token"], True)
    assert service.load(REF)["conversations"][CUSTOMER]["ficha"]["trabalho"] == "Enfermeira no hospital"

    read(service, [follow_up("c2", 1, "Somos dois adultos e um gato pequeno.", service)])
    email = card(service)
    assert parse_fichas('{"respostas": [{"id": "desconhecido", "ficha": {"trabalho": "x"}}]}',
                        service.pending()["properties"][0]) == []
    answer = {"respostas": [{"id": short_id("c2"), "reply_text": "Obrigado. Para quando precisam da casa?",
                             "ficha": {"agregado": "Dois adultos", "animais": "Um gato pequeno", "falta": []}}]}
    status, pasted = call("/api/paste", {"property_ref": REF, "text": json.dumps(answer)})
    assert status == 200
    ficha = service.load(REF)["conversations"][CUSTOMER]["ficha"]  # kept at once, before the reply goes out
    assert (ficha["trabalho"], ficha["agregado"], ficha["animais"]) == ("Enfermeira no hospital", "Dois adultos",
                                                                         "Um gato pequeno")
    assert "animais: Um gato pequeno" in reply_prompt(service.pending()["properties"][0], [email["id"]])

    [entry] = service.contacts()["fichas"]
    assert (entry["property_ref"], entry["email"], entry["phase"], entry["pending"]) == (REF, CUSTOMER, "qualificação", True)
    assert entry["known"] == 2 and entry["falta"] == ["datas", "disponibilidade"]
    assert entry["ficha"]["agregado"] == "Dois adultos" and entry["ficha"]["empresa"] is None

    service.set_ignored(REF, CUSTOMER, True, kind="grey")
    assert service.contacts()["fichas"] == []  # the lists are left out; they stay in the table below


def test_an_incomplete_file_never_holds_back_the_proposal_or_the_booking_but_every_booking_shows_it(service):
    read(service, [customer("1", "a@example.com")])
    draft_and_send(service, "1", "Olá.")
    service.propose_visits(REF, DAY, "17:00", "19:00", ["a@example.com"])
    [proposal] = service.pending()["properties"][0]["emails"]
    assert any("Ficha incompleta" in warning and "decides tu" in warning for warning in proposal["warnings"])
    prompt = reply_prompt(service.pending()["properties"][0], [proposal["id"]])
    assert ("para a visita ficar confirmada, precisamos ainda de saber: situação profissional e rendimentos, "
            "agregado familiar, datas ou duração do contrato, disponibilidade para visitas") in prompt

    revision = service.pending()["properties"][0]["revision"]
    service.drafts([{"id": proposal["id"], "reply_text": "Fica marcado às 17:30."}], revision, REF,
                   [{"id": proposal["id"], "visit_slot": f"{DAY} 17:30"}])
    preview = service.preview([proposal["id"]], REF)
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.send(preview["preview_token"], True, REF)
    [slot] = service.settings()["properties"][0]["visits"]["slots"]
    assert slot["ficha"]["complete"] is False and slot["ficha"]["known"] == 0

    data = service.load(REF)  # the missing answers arrive later: the booking shows it at once
    data["conversations"]["a@example.com"]["ficha"] = {"trabalho": "Professor", "agregado": "Casal", "datas": "2 anos",
                                                       "disponibilidade": "Tardes", "falta_extra": []}
    service.save(data, REF)
    [slot] = service.settings()["properties"][0]["visits"]["slots"]
    assert slot["ficha"]["complete"] is True
