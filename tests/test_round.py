import json
from unittest.mock import patch
import pytest
from backend.ai import parse_round, reply_prompt, round_prompt, short_id
from backend.store import load_visits
from test_properties import REF, SMTP, draft_and_send, read, service  # noqa: F401 (service is a fixture)
from test_visits import DAY, customer

NOTE = "O inquilino atual ainda lá está: a visita dura 20 minutos."


def two_customers(service):
    for key, email in (("1", "a@example.com"), ("2", "b@example.com")):
        read(service, [customer(key, email)])
        draft_and_send(service, key, "Olá.")


def answer(ids, **extra):
    """What the assistant sends back for a round: a text per language, a summary, each customer's greeting."""
    return json.dumps({"textos": {"pt": "🏠 Imóvel\n\nPropomos-lhe uma visita.\n\nCom os melhores cumprimentos,",
                                  "en": "🏠 Property\n\nWe would like to propose a visit.\n\nKind regards,"},
                       "resumos": {"de": "Wir schlagen einen Besichtigungstermin vor."},
                       "clientes": [{"id": short_id(ids[0]), "idioma": "pt", "lingua": "pt", "saudacao": "Cara Ana,"},
                                    {"id": short_id(ids[1]), "idioma": "en", "lingua": "de", "saudacao": "Dear Bruno,"},
                                    *extra.get("more", [])]})


def test_a_common_round_stays_out_of_the_cards_carries_its_knowledge_and_asks_for_one_text(service):
    two_customers(service)
    result = service.propose_visits(REF, DAY, "17:00", "19:00", ["a@example.com", "b@example.com"], NOTE, common=True)
    assert result["common"] and result["created"] == 2
    window = load_visits(service.folder, REF)["windows"][-1]
    assert window["note"] == NOTE
    queue = service.pending()["properties"][0]
    proposals = [email for email in queue["emails"] if email.get("kind") == "visit_proposal"]
    # The page leaves them out of Comunicações by this mark; the round panel lists them.
    assert {email["round"] for email in proposals} == {window["id"]}
    current = service.common_round(REF)
    assert [item["email"] for item in current["items"]] == ["a@example.com", "b@example.com"]
    assert current["window"]["note"] == NOTE and current["texts"] == {}

    prompt = round_prompt(queue, [item["id"] for item in current["items"]])
    for expected in (NOTE, "sempre pt-PT", "inglês para todos os outros", "não leva saudação", '"textos"'):
        assert expected in prompt
    # Never the customers' addresses.
    assert "a@example.com" not in prompt and "b@example.com" not in prompt


def test_the_common_text_becomes_every_draft_with_its_greeting_and_goes_out_to_all(service):
    two_customers(service)
    service.propose_visits(REF, DAY, "17:00", "19:00", ["a@example.com", "b@example.com"], common=True)
    ids = [item["id"] for item in service.common_round(REF)["items"]]
    queue = service.pending()["properties"][0]
    saved = service.save_round(REF, None, parse_round(answer(ids), queue, ids))
    assert {item["language"] for item in saved["items"]} == {"pt", "en"}
    drafts = {email["recipient"]["email"]: email["reply_text"] for email in service.pending()["properties"][0]["emails"]}
    assert drafts["a@example.com"].startswith("Cara Ana,\n\n🏠 Imóvel") and "Wir schlagen" not in drafts["a@example.com"]
    # English is the complete, official text; the short summary in their own language comes after it.
    assert drafts["b@example.com"].startswith("Dear Bruno,\n\n🏠 Property")
    assert drafts["b@example.com"].endswith("Kind regards,\n\n—\nWir schlagen einen Besichtigungstermin vor.")

    # Edited in the page: the new English text reaches its customer's draft.
    common = load_visits(service.folder, REF)["windows"][-1]["common"]
    common["texts"]["en"] = "We propose a visit tomorrow.\n\nKind regards,"
    service.save_round(REF, None, common)
    assert "We propose a visit tomorrow." in next(email["reply_text"] for email in service.pending()["properties"][0]["emails"]
                                                  if email["recipient"]["email"] == "b@example.com")

    preview = service.preview(ids, REF)
    SMTP.sent = []
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        result = service.send(preview["preview_token"], True, REF)
    assert [item["status"] for item in result["results"]] == ["sent", "sent"]
    conversations = service.load(REF)["conversations"]
    assert conversations["a@example.com"]["stage"] == 3 and conversations["b@example.com"]["visit_proposed"]
    assert service.common_round(REF)["items"] == []


def test_a_round_answer_missing_a_customer_or_a_language_is_refused(service):
    two_customers(service)
    service.propose_visits(REF, DAY, "17:00", "19:00", ["a@example.com", "b@example.com"], common=True)
    ids = [item["id"] for item in service.common_round(REF)["items"]]
    queue = service.pending()["properties"][0]
    partial = json.loads(answer(ids))
    partial["clientes"] = partial["clientes"][:1]
    with pytest.raises(ValueError, match="1 dos clientes"):
        parse_round(json.dumps(partial), queue, ids)
    no_english = json.loads(answer(ids))
    del no_english["textos"]["en"]
    with pytest.raises(ValueError, match="texto em inglês"):
        parse_round(json.dumps(no_english), queue, ids)


def test_individualizing_takes_one_customer_to_comunicacoes_with_the_round_knowledge(service):
    two_customers(service)
    service.propose_visits(REF, DAY, "17:00", "19:00", ["a@example.com", "b@example.com"], NOTE, common=True)
    first = service.common_round(REF)["items"][0]["id"]
    left = service.individual_round_item(REF, first)
    assert [item["email"] for item in left["items"]] == ["b@example.com"]
    queue = service.pending()["properties"][0]
    own = next(email for email in queue["emails"] if email["id"] == first)
    assert own["round"] is None
    # Written on its own, the proposal still says what the owner wanted this round to say.
    assert NOTE in reply_prompt(queue, [first])


def test_an_individual_round_is_the_one_card_per_customer_it_always_was(service):
    two_customers(service)
    result = service.propose_visits(REF, DAY, "17:00", "19:00", ["a@example.com", "b@example.com"], NOTE)
    assert not result["common"] and service.common_round(REF)["items"] == []


def test_the_round_panel_goes_from_the_prompt_to_the_send_through_the_page(service):
    from starlette.testclient import TestClient
    from backend.api import web_app
    client = TestClient(web_app(service.folder, "t"), base_url="http://127.0.0.1:8765")

    def call(path, body):
        response = client.post(path, json=body, headers={"X-Bot-Mail-Token": "t"})
        return response.status_code, response.json()

    two_customers(service)
    status, result = call("/api/visits/propose", {"property_ref": REF, "day": DAY, "start": "17:00", "end": "19:00",
                                                  "emails": ["a@example.com", "b@example.com"], "note": NOTE, "common": True})
    assert status == 200 and result["common"]
    status, prompt = call("/api/visits/round-prompt", {"property_ref": REF})
    assert status == 200 and NOTE in prompt["prompt"]
    ids = [item["id"] for item in call("/api/visits/round", {"property_ref": REF})[1]["items"]]
    status, pasted = call("/api/visits/round-paste", {"property_ref": REF, "text": answer(ids)})
    assert status == 200 and pasted["texts"]["pt"].startswith("🏠 Imóvel")
    assert call("/api/visits/round-paste", {"property_ref": REF, "text": "sem json"})[0] == 400
    status, preview = call("/api/preview", {"property_ref": REF, "ids": ids})
    assert status == 200 and len(preview["replies"]) == 2
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        status, sent = call("/api/send", {"property_ref": REF, "preview_token": preview["preview_token"], "confirmed": True})
    assert status == 200 and [item["status"] for item in sent["results"]] == ["sent", "sent"]
