"""After the visit: who came, a private and a public note, the thanks with the survey and the visit sheet."""
from datetime import date, datetime, timezone
import pytest
from backend.ai import AFTER_VISIT_RULE, AFTER_VISIT_TEMPLATE, parse_survey, reply_prompt
from backend.store import load_visits, save_visits
from test_properties import CUSTOMER, REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

TODAY = date.today().isoformat()


def booked(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    agenda = load_visits(service.folder, REF)
    agenda["slots"].append({"at": f"{TODAY} 13:00", "customer": CUSTOMER, "name": "Ana Exemplo"})
    save_visits(service.folder, REF, agenda)


def test_the_thanks_carries_the_public_note_never_the_private_one(service):
    booked(service)
    with pytest.raises(ValueError, match="apareceu"):
        service.visit_thanks(REF, CUSTOMER)
    service.check_visit(REF, CUSTOMER, True, "Pareceu hesitante com a renda.", "Foi um prazer mostrar-lhe a cozinha.")
    [slot] = load_visits(service.folder, REF)["slots"]
    assert slot["check"]["attended"] is True and slot["check"]["private"] == "Pareceu hesitante com a renda."
    key = service.visit_thanks(REF, CUSTOMER)["id"]
    with pytest.raises(ValueError, match="já está na fila"):
        service.visit_thanks(REF, CUSTOMER)
    queue = service.pending()["properties"][0]
    [item] = queue["emails"]
    assert item["kind"] == "visit_thanks" and item["visit_done"]["public"] == "Foi um prazer mostrar-lhe a cozinha."
    prompt = reply_prompt(queue, [key])
    assert "interação: pós-visita" in prompt and "Foi um prazer mostrar-lhe a cozinha." in prompt
    assert "hesitante" not in prompt  # the private note never reaches the assistant
    assert AFTER_VISIT_RULE[:40] in prompt and "FICHA DE VISITA" in prompt

    stage = service.load(REF)["conversations"][CUSTOMER]["stage"]
    draft_and_send(service, key, "Obrigado pela visita. 1. O imóvel: …")
    conversation = service.load(REF)["conversations"][CUSTOMER]
    assert conversation["stage"] == stage and conversation["visit_check"]["thanks_sent_at"]

    # The customer answers by replying: the survey is kept on the customer and shown with the visit.
    ours = conversation["sent_message_ids"][-1]
    read(service, [{"gmail_message_id": "s1", "from": [{"email": CUSTOMER}], "in_reply_to": ours,
                    "date": datetime.now(timezone.utc).isoformat(), "subject": "Re: Obrigado pela visita",
                    "body_text": "1. O imóvel: 5\n2. O consultor: 4\n3. A marcação: 5\n4. Continua interessado? sim\n"
                                 "5. Comentário: quando posso entrar?\nConfirmo a visita"}])
    survey = service.load(REF)["conversations"][CUSTOMER]["visit_survey"]
    assert (survey["imovel"], survey["consultor"], survey["marcacao"], survey["interesse"], survey["ficha_confirmada"]) == (
        5, 4, 5, "sim", True)
    [shown] = next(p for p in service.settings()["properties"] if p["reference"] == REF)["visits"]["slots"]
    assert shown["survey"]["imovel"] == 5 and shown["check"]["attended"] is True


def test_a_customer_without_a_visit_cannot_be_checked_and_a_no_show_gets_no_thanks(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    with pytest.raises(ValueError, match="não tem visita"):
        service.check_visit(REF, CUSTOMER, True)
    agenda = load_visits(service.folder, REF)
    agenda["slots"].append({"at": f"{TODAY} 13:00", "customer": CUSTOMER})
    save_visits(service.folder, REF, agenda)
    service.check_visit(REF, CUSTOMER, False, "Não avisou.", "")
    with pytest.raises(ValueError, match="apareceu"):
        service.visit_thanks(REF, CUSTOMER)


def test_the_survey_reader_takes_numbered_answers_in_any_of_the_languages_and_nothing_else():
    assert parse_survey("1) The property: 4/5\n2) The consultant: 5\n4) Still interested? maybe\nI confirm the visit") == {
        "imovel": 4, "consultor": 5, "marcacao": None, "interesse": "talvez", "comentario": None, "ficha_confirmada": True}
    assert parse_survey("Obrigado, gostei muito da casa.") is None


def test_the_after_visit_texts_left_as_they_came_keep_following_the_code(service):
    service.save_voice({"greeting": "formal", "languages": "pt_en_fr", "closing": "cordial", "signature": "Equipa",
                        "after_visit": AFTER_VISIT_RULE, "after_visit_template": "1. A casa:\n2. O consultor:"})
    voice = service.settings()["voice"]
    assert voice["after_visit"] == AFTER_VISIT_RULE and voice["after_visit_template"] == "1. A casa:\n2. O consultor:"
    assert AFTER_VISIT_TEMPLATE != voice["after_visit_template"]
