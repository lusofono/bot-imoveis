"""The survey answer: thanked by the assistant, a bad mark flagged, and read on dials (property and Painel)."""
from datetime import datetime, timezone
from backend.ai import reply_prompt
from backend.rules import quality, survey_alerts, survey_report
from test_after_visit import booked
from test_properties import CUSTOMER, REF, draft_and_send, read, service  # noqa: F401 (service is a fixture)


def test_the_dial_weighs_the_ones_hardest():
    assert quality([]) is None and quality([7, None]) is None
    assert quality([5, 5, 5]) == 100 and quality([1, 1]) == 0 and quality([3]) == 50
    # Three 1s and three 5s: a plain mean would say 50; the 1s weigh three times, so it reads 25.
    assert quality([1, 1, 1, 5, 5, 5]) == 25
    assert quality([2, 5]) < quality([4, 5])
    assert survey_alerts({"imovel": 5, "consultor": 1, "marcacao": 2, "interesse": "não"}) == [
        "Consultor: 1/5", "Marcação e emails: 2/5", "já não tem interesse"]
    assert survey_alerts({"imovel": 3, "consultor": 4, "interesse": "talvez"}) == []
    report = survey_report([{"imovel": 5, "consultor": 1}, {"imovel": 4, "interesse": "sim"}, None])
    assert report["responses"] == 2 and report["parts"]["imovel"]["average"] == 4.5
    assert report["parts"]["consultor"] == {"label": "Consultor", "score": 0, "count": 1, "average": 1.0, "ones": 1}
    assert report["parts"]["marcacao"]["score"] is None and report["alerts"] == 1 and report["interest"]["sim"] == 1


def test_a_bad_survey_answer_is_flagged_thanked_and_counted(service):
    booked(service)
    service.check_visit(REF, CUSTOMER, True)
    key = service.visit_thanks(REF, CUSTOMER)["id"]
    draft_and_send(service, key, "Obrigado pela visita. 1. O imóvel: …")
    ours = service.load(REF)["conversations"][CUSTOMER]["sent_message_ids"][-1]
    read(service, [{"gmail_message_id": "s1", "from": [{"email": CUSTOMER}], "in_reply_to": ours,
                    "date": datetime.now(timezone.utc).isoformat(), "subject": "Re: Obrigado pela visita",
                    "body_text": "1. O imóvel: 4\n2. O consultor: 1\n3. A marcação: 5\n4. Continua interessado? não\n"
                                 "5. Comentário: o consultor chegou atrasado"}])
    [email] = service.pending()["properties"][0]["emails"]
    assert email["survey_reply"]["alerts"] == ["Consultor: 1/5", "já não tem interesse"]
    assert any(warning.startswith("Atenção ao inquérito") for warning in email["warnings"])
    queue = service.pending()["properties"][0]
    prompt = reply_prompt(queue, [email["id"]])
    assert "interação: resposta ao inquérito" in prompt and "o consultor chegou atrasado" in prompt
    assert "Resposta ao inquérito (emails marcados «resposta ao inquérito»): Quando o cliente" in queue["instructions"]

    [property_] = service.settings()["properties"]
    report = property_["survey_report"]
    assert report["responses"] == 1 and report["alerts"] == 1 and report["parts"]["consultor"]["score"] == 0
    assert report["answers"][0]["name"] == "Ana Exemplo" and report["answers"][0]["comment"] == "o consultor chegou atrasado"
    assert service.metrics(14)["quality"]["parts"]["imovel"]["score"] == 75
    tasks = {task["kind"]: task for task in service.todo()["tasks"]}
    assert tasks["survey_alert"]["names"] == ["Ana Exemplo"] and "reply" not in tasks  # not counted twice


def test_marks_in_words_over_wrapped_lines_are_read_and_old_answers_are_repaired(service):
    from backend.ai import parse_survey
    reply = ("1. O imóvel: *Excelente.*\n2. O consultor que o recebeu na visita:* Muito bom.*\n"
             "3. A marcação da visita e a troca de emails (rapidez, clareza, respostas às\nsuas dúvidas): *Razoável*\n"
             "4. Continua interessado em arrendar este imóvel? (sim / não / talvez): *Não*\n"
             "5. Comentário ou dúvida (opcional): *O ar condicionado.*\n\nObrigada.\n\nEm sex., 25/09 escreveu:\n"
             "> 4. Continua interessado em arrendar este imóvel? (sim / não / talvez):")
    assert parse_survey(reply) == {"imovel": 5, "consultor": 4, "marcacao": 3, "interesse": "não",
                                   "comentario": "O ar condicionado.", "ficha_confirmada": False}
    booked(service)
    data = service.load(REF)
    conversation = data["conversations"][CUSTOMER]
    conversation["visit_survey"] = {"imovel": None, "consultor": None, "marcacao": None, "interesse": "sim",
                                    "comentario": None, "ficha_confirmada": False, "at": "2026-09-25"}  # as read before
    conversation["history"].append({"who": "cliente", "text": reply, "at": "2026-09-25"})
    service.save(data, REF)
    read(service, [])
    survey = service.load(REF)["conversations"][CUSTOMER]["visit_survey"]
    assert (survey["imovel"], survey["consultor"], survey["marcacao"], survey["interesse"], survey["at"]) == (
        5, 4, 3, "não", "2026-09-25")


def test_an_answer_that_describes_instead_of_marking():
    from backend.ai import survey_mark
    assert survey_mark("*Rápida e Clara.*") == 5 and survey_mark("Muito lenta") == 2
    assert survey_mark("Razoável, mas rápida") == 3  # a mark word wins over a description
    assert survey_mark("nada a dizer") is None


def test_the_fourth_dial_is_the_interest():
    report = survey_report([{"interesse": "sim"}, {"interesse": "talvez"}, {"interesse": "não"}, {"imovel": 5}])
    assert report["parts"]["interesse"] == {"label": "Interesse em arrendar", "count": 3, "average": None, "ones": 0, "no": 1,
                                            "score": 50}
    assert survey_report([])["parts"]["interesse"]["score"] is None  # no answer: the needle rests at the middle


def test_a_survey_answer_read_before_its_mark_gets_it_at_the_next_read():
    # 27/09: read before 26/09, it went to the assistant as a plain «8.ª interação», which has no prompt.
    from backend.service import MailService, SURVEY_NOTICE
    text = ("1. O imóvel: Excelente\n2. O consultor: Excelente\n3. A marcação: Rápida e clara\n"
            "4. Continua interessado? sim\n5. Comentário: o ar condicionado não parecia funcionar")
    item = {"id": "s1", "kind": "follow_up", "reply_status": "pending", "recipient": {"email": "ana@example.com"},
            "customer": {"message": text}, "warnings": ["Resposta ao inquérito pós-visita registada (vê-a na Agenda)."]}
    data = {"emails": [item], "conversations": {"ana@example.com": {"visit_check": {"thanks_sent_at": "2026-09-25T10:00:00"}}}}
    MailService.repair_surveys(data)
    assert item["survey_reply"] == {"alerts": []} and item["warnings"] == [SURVEY_NOTICE]
    # Not after the thanks (no survey sent): left alone.
    other = {**item, "id": "s2", "recipient": {"email": "rui@example.com"}}
    other.pop("survey_reply")
    data = {"emails": [other], "conversations": {"rui@example.com": {}}}
    MailService.repair_surveys(data)
    assert "survey_reply" not in other
