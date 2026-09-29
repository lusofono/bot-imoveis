"""The Oficina (29/09): token prices typed by the owner, and the test platform, whose customers write from the account
itself (Gmail keeps no other sender) with the X-ARIA-Teste mark and themselves in the Reply-To."""
import json
from unittest.mock import patch
import pytest
from backend import testlab
from backend.openai_client import BUILTIN_PRICES, apply_prices, estimate_cost_usd
from backend.store import load_json, save_json
from test_properties import IDEALISTA, REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

ACCOUNT = "owner@example.com"
TEST_REF = "AP_teste1"


@pytest.fixture(autouse=True)
def table_prices():
    yield
    apply_prices({})  # the price table is the module's: never leak one test's prices into the next


def with_test_property(service):
    service.save_property({"reference": TEST_REF, "description": "Penthouse T3 no Chiado", "listing_id": "99990001",
                           "sender": ACCOUNT, "advertised_rent_eur": 3200})
    path = service.folder / "properties" / TEST_REF / "profile.json"
    profile = load_json(path, {})
    profile["test"] = True
    save_json(path, profile)


def marked_notice(key, client="owner+cd1@example.com", name="Sergii Sviatokha", test=True):
    item = lead(key, reply_to=(client,), ref=TEST_REF, listing="99990001", body_email=client,
                sender={"name": "idealista (teste)", "email": ACCOUNT})
    item["subject"] = f"Mensagem de teste de {name} sobre o teu imóvel, com ref: {TEST_REF}"
    if test:
        item["test"] = True
    return item


def queue_of(service, ref):
    return next(queue for queue in service.pending()["properties"] if queue["property_ref"] == ref)


def test_the_owner_changes_a_price_adds_a_model_and_puts_the_table_back(service):
    service.set_price("gpt-4o-mini", "0,30", 1.2)
    assert estimate_cost_usd("gpt-4o-mini", 1000, 1000) == pytest.approx(0.0003 + 0.0012)
    ai = service.set_price("gpt-6-nova", 1, 4)
    nova = next(model for model in ai["models"] if model["id"] == "gpt-6-nova")
    assert (nova["builtin"], nova["edited"], nova["input_usd_per_1m"]) == (False, True, 1)
    assert service.set_model("gpt-6-nova")["model"] == "gpt-6-nova"
    with pytest.raises(ValueError, match="motor em uso"):
        service.set_price("gpt-6-nova", reset=True)
    service.set_model("gpt-4o-mini")
    service.set_price("gpt-6-nova", reset=True)
    ai = service.set_price("gpt-4o-mini", reset=True)
    assert "gpt-6-nova" not in {model["id"] for model in ai["models"]}
    assert estimate_cost_usd("gpt-4o-mini", 1000, 0) == pytest.approx(BUILTIN_PRICES["gpt-4o-mini"][0])
    for bad in (("gpt-4o", "x", 1), ("gpt-4o", 0, 1), ("nome com espaços", 1, 1)):
        with pytest.raises(ValueError):
            service.set_price(*bad)


def test_a_marked_notice_from_the_account_is_a_lead_of_the_test_property_only(service):
    with_test_property(service)
    read(service, [marked_notice("t1"), marked_notice("t2", "owner+cd2@example.com", "Ana Teste", test=False)])
    [email] = queue_of(service, TEST_REF)["emails"]
    # The name without «teste de», the customer from the Reply-To; the unmarked one (the owner's own) is never read.
    assert email["customer"]["name"] == "Sergii Sviatokha" and email["recipient"]["email"] == "owner+cd1@example.com"
    assert queue_of(service, REF)["emails"] == []
    # A real property never takes a marked notice, even with its own sender and reference.
    marked = lead("r1")
    marked["test"] = True
    read(service, [marked])
    assert queue_of(service, REF)["emails"] == []


def test_a_test_customer_replies_from_the_account_and_is_known_by_the_reply_to(service):
    with_test_property(service)
    read(service, [marked_notice("t1")])
    service.drafts([{"id": "t1", "reply_text": "Olá."}], queue_of(service, TEST_REF)["revision"], TEST_REF)
    preview = service.preview(["t1"], TEST_REF)
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.send(preview["preview_token"], True, TEST_REF)
    ours = service.load(TEST_REF)["conversations"]["owner+cd1@example.com"]["sent_message_ids"][-1]
    reply = {"gmail_message_id": "t3", "from": [{"name": "Sergii", "email": ACCOUNT}], "test": True,
             "reply_to": [{"name": "Sergii", "email": "owner+cd1@example.com"}], "in_reply_to": ours,
             "subject": "Re: resposta", "body_text": "Somos dois adultos."}
    read(service, [reply])
    [email] = queue_of(service, TEST_REF)["emails"]
    assert email["kind"] == "follow_up" and email["recipient"]["email"] == "owner+cd1@example.com" and not email["blocked"]


def test_generating_clients_sends_each_notice_and_a_copy_for_the_consultant(service):
    with_test_property(service)
    invented = {"clientes": [{"nome": "Sergii Sviatokha", "lingua": "uk", "mensagem": "Ainda está disponível?",
                              "perfil": {"agregado": "casal", "segredos": "tem um gato"}},
                             {"nome": "Ana Teste", "lingua": "pt-PT", "mensagem": "Tem garagem?", "perfil": {}}]}
    testlab.set_contest(service, True, "consultor@example.com")
    with pytest.raises(ValueError, match="desta conta"):
        testlab.set_contest(service, True, ACCOUNT)
    SMTP.sent = []
    with patch("backend.testlab.complete", return_value=(json.dumps(invented), {"prompt_tokens": 100, "completion_tokens": 50})), \
            patch("backend.testlab.openai_api_key", return_value="k"), patch("backend.testlab.app_password", return_value="p"), \
            patch("backend.testlab.smtplib.SMTP_SSL", SMTP):
        result = testlab.generate_clients(service, 2, "2026-09-29T12:00:00+01:00")
    assert result["created"] == ["Sergii Sviatokha", "Ana Teste"]
    ours = [msg for msg in SMTP.sent if msg["To"] == ACCOUNT]
    copies = [msg for msg in SMTP.sent if msg["To"] == "consultor@example.com"]
    assert len(ours) == len(copies) == 2
    assert {msg["X-ARIA-Teste"] for msg in ours} == {"1"} and {msg["X-ARIA-Teste"] for msg in copies} == {"consultor"}
    assert ours[0]["Reply-To"] == "Sergii Sviatokha <owner+cd1@example.com>" and ours[1]["Reply-To"].endswith("<owner+cd2@example.com>")
    assert ours[0]["Subject"] == f"Mensagem de teste de Sergii Sviatokha sobre o teu imóvel, com ref: {TEST_REF}"
    assert copies[0]["Subject"].startswith("[consultor] ")
    # The hidden profile stays in the lab's file, never in what the page gets.
    assert "segredos" not in json.dumps(result)
    assert load_json(service.folder / "teste" / "clientes.json", {})["clients"][0]["profile"]["segredos"] == "tem um gato"
    # Read back, the page's copy is a lead of the test property, with the customer the notice names.
    body = ours[0].get_content()
    item = marked_notice("g1")
    item["body_text"] = body
    read(service, [item])
    [email] = queue_of(service, TEST_REF)["emails"]
    assert email["customer"]["message"] == "Ainda está disponível?" and email["customer"]["phone"] == "900 000 001"


def test_the_oficina_needs_admin_and_a_test_property(service):
    from starlette.testclient import TestClient
    from backend.api import web_app
    client = TestClient(web_app(service.folder, "t"), base_url="http://127.0.0.1:8765")
    call = lambda path, body: client.post(path, json=body, headers={"X-Bot-Mail-Token": "t"})
    assert call("/api/testlab/state", {}).status_code == 400
    assert service.settings()["admin"] is False
    config = load_json(service.folder / "config.json", {})
    save_json(service.folder / "config.json", {**config, "admin": True})
    assert call("/api/testlab/state", {}).json()["property_ref"] is None
    with pytest.raises(ValueError, match="imóvel de teste"):
        testlab.generate_clients(service, 1, "2026-09-29T12:00:00+01:00")
    with_test_property(service)
    assert call("/api/testlab/state", {}).json()["property_ref"] == TEST_REF
    assert call("/api/ai/price", {"model": "gpt-4o", "input_usd_per_1m": 3, "output_usd_per_1m": 12}).status_code == 200


def test_the_consultant_gets_the_copies_that_are_missing(service):
    with_test_property(service)
    invented = {"clientes": [{"nome": "Ana Teste", "lingua": "pt-PT", "mensagem": "Tem garagem?", "perfil": {}}]}
    SMTP.sent = []
    with patch("backend.testlab.complete", return_value=(json.dumps(invented), {"prompt_tokens": 1, "completion_tokens": 1})), \
            patch("backend.testlab.openai_api_key", return_value="k"), patch("backend.testlab.app_password", return_value="p"), \
            patch("backend.testlab.smtplib.SMTP_SSL", SMTP):
        testlab.generate_clients(service, 1, "2026-09-29T12:00:00+01:00")  # the contest off: no copy
        with pytest.raises(ValueError, match="Human contest"):
            testlab.send_to_consultant(service)
        testlab.set_contest(service, True, "consultor@example.com")
        assert testlab.send_to_consultant(service)["sent"] == 1
        assert testlab.send_to_consultant(service)["sent"] == 0  # never twice
    assert [msg["To"] for msg in SMTP.sent] == [ACCOUNT, "consultor@example.com"]


def test_wiping_starts_the_test_property_over_and_never_reuses_an_address(service):
    with_test_property(service)
    read(service, [marked_notice("t1")])
    lab = testlab.load_lab(service.folder)
    lab["clients"] = [{"number": 1, "name": "Sergii Sviatokha", "address": "owner+cd1@example.com"}]
    testlab.save_lab(service.folder, lab)
    assert testlab.set_contest(service, False, "", 25)["new_percent"] == 25
    with pytest.raises(ValueError, match="0 a 100"):
        testlab.set_contest(service, False, "", 150)
    result = testlab.wipe(service)
    assert result["removed"] == 1 and result["clients"] == [] and result["new_percent"] == 25
    assert queue_of(service, TEST_REF)["emails"] == [] and service.load(TEST_REF)["conversations"] == {}
    read(service, [marked_notice("t1")])  # the same email, still in the inbox: never back
    assert queue_of(service, TEST_REF)["emails"] == []
    assert testlab.load_lab(service.folder)["next_number"] == 2
