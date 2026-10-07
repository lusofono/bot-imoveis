"""07/10, «Negócio fechado»: one email to every customer of the property (active, all or not active, each switched on or
off), the same text for all in their language with a short survey, then the property closes and goes to the archive;
and the archive itself — out of the usual views, back with «Reativar»."""
import json
from unittest.mock import patch
import pytest
from backend.ai import DEAL_CLOSED_TEMPLATE, deal_round_prompt, parse_round, short_id
from backend.rules import deal_survey, property_archived
from backend.store import load_json, load_visits, save_visits
from test_merge import follow_up
from test_properties import CUSTOMER, REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)
from test_visits import customer

NOTE = "Agradecer também a quem visitou no sábado."


def three_customers(service):
    """Ana (active), Bruno (inactive) and Carla (the selected one), all already written to."""
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    for key, email in (("2", "bruno@example.com"), ("3", "carla@example.com")):
        read(service, [customer(key, email)])
        draft_and_send(service, key, "Olá.")
    data = service.load(REF)
    data["conversations"]["bruno@example.com"]["inactive"] = {"at": "2026-10-01", "reason": "quatro emails sem resposta"}
    data["conversations"]["carla@example.com"]["selection"] = {"status": "chosen"}
    service.save(data, REF)


def answer(ids):
    return json.dumps({"textos": {"pt": "O imóvel já foi arrendado.\n\n" + DEAL_CLOSED_TEMPLATE + "\n\nCom os melhores cumprimentos,"},
                       "resumos": {}, "clientes": [{"id": short_id(key), "idioma": "pt", "lingua": "pt",
                                                    "saudacao": "Caro cliente,"} for key in ids]})


def send(service, ids):
    preview = service.preview(ids, REF)
    SMTP.sent = []
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        return service.send(preview["preview_token"], True, REF)


def test_who_the_deal_email_can_go_to(service):
    three_customers(service)
    read(service, [customer("4", "dora@example.com")])  # a new request, never answered: left out (answered in Emails)
    found = service.deal_candidates(REF)
    people = {person["email"]: person for person in found["customers"]}
    assert set(people) == {CUSTOMER, "bruno@example.com", "carla@example.com"}
    assert people[CUSTOMER]["active"] and not people["bruno@example.com"]["active"]
    assert people["carla@example.com"]["selected"] and not people[CUSTOMER]["selected"]
    assert found["left_out"]["waiting"] == ["dora@example.com"]
    service.set_ignored(REF, "bruno@example.com", True, kind="black")
    assert "bruno@example.com" not in {person["email"] for person in service.deal_candidates(REF)["customers"]}


def test_one_text_for_all_then_the_property_closes_and_goes_to_the_archive(service):
    three_customers(service)
    current = service.prepare_deal_round(REF, [CUSTOMER, "bruno@example.com", "nobody@example.com"], NOTE)
    assert [item["email"] for item in current["items"]] == [CUSTOMER, "bruno@example.com"]  # only known customers
    with pytest.raises(ValueError, match="Já há um email"):
        service.prepare_deal_round(REF, [CUSTOMER], "")
    queue = service.pending()["properties"][0]
    ids = [item["id"] for item in current["items"]]
    assert all(email.get("round") for email in queue["emails"] if email["id"] in ids)  # out of the Emails cards
    rule, template, note = service.deal_texts(REF)
    prompt = deal_round_prompt(queue, ids, rule, template, note)
    for expected in ("já foi arrendado", "1. A rapidez das nossas respostas", NOTE, "sempre pt-PT", '"textos"'):
        assert expected in prompt
    assert CUSTOMER not in prompt and "bruno@example.com" not in prompt

    saved = service.save_deal_round(REF, parse_round(answer(ids), queue, ids))
    assert all(item["has_draft"] for item in saved["items"])
    result = send(service, ids)
    assert [item["status"] for item in result["results"]] == ["sent", "sent"]
    conversations = service.load(REF)["conversations"]
    assert conversations[CUSTOMER]["deal_closed_sent_at"] and conversations[CUSTOMER]["stage"] == 1  # no step spent
    profile = load_json(service.folder / "properties" / REF / "profile.json", {})
    assert property_archived(profile)["label"] == "Negócio fechado"
    agenda = load_visits(service.folder, REF)
    assert agenda["closed_at"] and agenda["closed_by"] == "negocio"
    assert service.deal_round(REF)["finished_at"] and service.deal_round(REF)["sent"] == 2
    settings = next(item for item in service.settings()["properties"] if item["reference"] == REF)
    assert settings["archived"]["reason"] == "fechado" and settings["deal_round"]["sent"] == 2
    assert service.pending()["properties"][0]["archived"]
    assert "já não está disponível" in service.pending()["properties"][0]["instructions"]

    # The answer to its survey is read and kept on the customer
    read(service, [follow_up("c9", 1, "1: 5\n2: 4\n3:\n4: sim\n5: Muito profissionais.", service)])
    [reply] = [email for email in service.pending()["properties"][0]["emails"] if email["id"] == "c9"]
    assert reply["survey_reply"]["deal"] and any("negócio fechado" in warning for warning in reply["warnings"])
    survey = service.load(REF)["conversations"][CUSTOMER]["deal_survey"]
    assert (survey["respostas"], survey["informacao"], survey["visita"], survey["recomenda"]) == (5, 4, None, "sim")
    report = next(item for item in service.settings()["properties"] if item["reference"] == REF)["deal_round"]["survey"]
    assert report["responses"] == 1 and report["parts"]["respostas"]["average"] == 5
    assert report["comments"] == ["Muito profissionais."]


def test_cancelling_takes_the_emails_out_and_sends_nothing(service):
    three_customers(service)
    service.prepare_deal_round(REF, [CUSTOMER], "")
    assert service.cancel_deal_round(REF)["cancelled"] == 1
    assert service.deal_round(REF)["items"] == [] and not service.load(REF).get("deal_round")
    assert not property_archived(load_json(service.folder / "properties" / REF / "profile.json", {}))


def test_the_archive_has_a_reason_and_reactivating_opens_what_it_closed(service):
    with pytest.raises(ValueError, match="motivo"):
        service.archive_property(REF, "esquecido")
    service.archive_property(REF, "pausa")
    assert property_archived(load_json(service.folder / "properties" / REF / "profile.json", {}))["label"] == "Em pausa"
    assert not load_visits(service.folder, REF).get("closed_at")  # a pause closes nothing
    service.unarchive_property(REF)
    with pytest.raises(ValueError, match="não está no arquivo"):
        service.unarchive_property(REF)

    service.archive_property(REF, "fechado")  # by hand: the visits close too
    assert load_visits(service.folder, REF)["closed_by"] == "arquivo"
    service.unarchive_property(REF)
    assert not load_visits(service.folder, REF).get("closed_at")
    # visits closed by «Fechar visitas» stay closed when the property comes back from the archive
    agenda = load_visits(service.folder, REF)
    agenda["closed_at"] = "2026-10-01T10:00:00+00:00"
    save_visits(service.folder, REF, agenda)
    service.archive_property(REF, "fechado")
    service.unarchive_property(REF)
    assert load_visits(service.folder, REF)["closed_at"] == "2026-10-01T10:00:00+00:00"


def test_the_deal_survey_reads_the_numbers_as_its_own_questions():
    from backend.ai import parse_survey
    survey = deal_survey(parse_survey("1. A rapidez das nossas respostas: 2\n2. A clareza: 5\n4. Recomendaria? não"))
    assert (survey["respostas"], survey["informacao"], survey["recomenda"]) == (2, 5, "não")
    assert deal_survey(None) is None


def test_the_sales_deal_email_says_sold(service):
    service.save_property({"reference": REF, "description": "Moradia T4", "deal": "venda"})
    rule, template, _ = service.deal_texts(REF)
    assert "já foi vendido" in rule and "arrendado" not in rule and template == DEAL_CLOSED_TEMPLATE


def test_the_deal_panel_goes_from_the_customers_to_the_archive_through_the_page(service):
    from starlette.testclient import TestClient
    from backend.api import web_app
    client = TestClient(web_app(service.folder, "t"), base_url="http://127.0.0.1:8765")

    def call(path, body=None):
        response = (client.get(path, headers={"X-Bot-Mail-Token": "t"}) if body is None
                    else client.post(path, json=body, headers={"X-Bot-Mail-Token": "t"}))
        return response.status_code, response.json()

    three_customers(service)
    status, found = call("/api/property/deal-candidates", {"property_ref": REF})
    assert status == 200 and len(found["customers"]) == 3
    status, prepared = call("/api/property/deal-prepare", {"property_ref": REF, "emails": [CUSTOMER], "note": NOTE})
    assert status == 200 and len(prepared["items"]) == 1
    status, prompt = call("/api/property/deal-prompt", {"property_ref": REF})
    assert status == 200 and NOTE in prompt["prompt"] and "Recomendaria a nossa agência?" in prompt["prompt"]
    ids = [item["id"] for item in prepared["items"]]
    status, pasted = call("/api/property/deal-paste", {"property_ref": REF, "text": answer(ids)})
    assert status == 200 and pasted["texts"]["pt"].startswith("O imóvel já foi arrendado.")
    status, preview = call("/api/preview", {"property_ref": REF, "ids": ids})
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        status, sent = call("/api/send", {"property_ref": REF, "preview_token": preview["preview_token"], "confirmed": True})
    assert status == 200 and [item["status"] for item in sent["results"]] == ["sent"]
    status, settings = call("/api/settings")
    assert next(item for item in settings["properties"] if item["reference"] == REF)["archived"]["reason"] == "fechado"
    status, back = call("/api/property/unarchive", {"reference": REF})
    assert status == 200 and not next(item for item in back["settings"]["properties"] if item["reference"] == REF)["archived"]
    status, again = call("/api/property/archive", {"reference": REF, "reason": "desistimos"})
    assert next(item for item in again["settings"]["properties"] if item["reference"] == REF)["archived"]["label"] == "Desistimos nós"
    assert call("/api/property/archive", {"reference": REF, "reason": "x"})[0] == 400


def test_the_closing_value_goes_to_the_archive_and_never_to_the_ai(service):
    three_customers(service)
    with pytest.raises(ValueError, match="Valor de fecho"):
        service.prepare_deal_round(REF, [CUSTOMER], "", "muito")
    current = service.prepare_deal_round(REF, [CUSTOMER], "", "1.450 €")
    assert current["price"] == 1450
    ids = [item["id"] for item in current["items"]]
    queue = service.pending()["properties"][0]
    rule, template, note = service.deal_texts(REF)
    assert "1450" not in deal_round_prompt(queue, ids, rule, template, note) and "1450" not in queue["instructions"]
    service.save_deal_round(REF, parse_round(answer(ids), queue, ids))
    send(service, ids)
    archived = property_archived(load_json(service.folder / "properties" / REF / "profile.json", {}))
    assert archived["price"] == 1450
    assert service.set_closing_price(REF, "1500")["price"] == 1500
    assert service.set_closing_price(REF, "")["price"] is None
    assert "price" not in load_json(service.folder / "properties" / REF / "profile.json", {})["archived"]


def test_archiving_by_hand_asks_the_value_only_for_a_deal_closed(service):
    service.archive_property(REF, "pausa", "1500")
    assert "price" not in load_json(service.folder / "properties" / REF / "profile.json", {})["archived"]
    with pytest.raises(ValueError, match="só para um imóvel arquivado como negócio fechado"):
        service.set_closing_price(REF, "1500")
    service.unarchive_property(REF)
    service.archive_property(REF, "fechado", "1.500,50")
    assert load_json(service.folder / "properties" / REF / "profile.json", {})["archived"]["price"] == 1500.5
    with pytest.raises(ValueError, match="Valor de fecho"):
        service.set_closing_price(REF, "2.000.000")  # a rent of two million: refused
