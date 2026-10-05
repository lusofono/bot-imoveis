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
    with patch("backend.testlab.complete", return_value=(json.dumps(invented), {"prompt_tokens": 100, "completion_tokens": 50})) as ai, \
            patch("backend.testlab.openai_api_key", return_value="k"), patch("backend.testlab.app_password", return_value="p"), \
            patch("backend.testlab.smtplib.SMTP_SSL", SMTP):
        result = testlab.generate_clients(service, 2, "2026-09-29T12:00:00+01:00")
    assert ai.call_args.kwargs["effort"] == "none"  # 02/10: the test customers need no reasoning
    assert result["created"] == ["Sergii Sviatokha", "Ana Teste"]
    ours = [msg for msg in SMTP.sent if msg["To"] == ACCOUNT]
    copies = [msg for msg in SMTP.sent if msg["To"] == "consultor@example.com"]
    assert len(ours) == len(copies) == 2
    assert {msg["X-ARIA-Teste"] for msg in ours} == {"1"} and {msg["X-ARIA-Teste"] for msg in copies} == {"consultor"}
    assert ours[0]["Reply-To"] == "Sergii Sviatokha <owner+cd1@example.com>" and ours[1]["Reply-To"].endswith("<owner+cd2@example.com>")
    assert ours[0]["Subject"] == f"TEST! Mensagem de teste de Sergii Sviatokha sobre o teu imóvel, com ref: {TEST_REF}"
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


def test_the_conversations_come_out_as_one_text_file_with_the_hidden_profile_and_the_marks(service):
    # 02/10: «Descarregar as conversas», to read the whole test at leisure (before a wipe, say)
    with_test_property(service)
    read(service, [marked_notice("t1")])
    lab = testlab.load_lab(service.folder)
    lab["clients"] = [{"number": 1, "name": "Sergii Sviatokha", "language": "uk", "address": "owner+cd1@example.com",
                       "message": "Ainda está disponível?", "profile": {"agregado": "dois adultos", "segredos": "um gato"},
                       "created_at": "2026-10-02T10:00:00+01:00"},
                      {"number": 2, "name": "Ana Nova", "address": "owner+cd2@example.com",
                       "message": "Olá, posso visitar?", "created_at": "2026-10-02T10:05:00+01:00"}]
    lab["evaluations"] = [{"at": "2026-10-02T11:00:00+01:00", "number": 1, "name": "Sergii Sviatokha", "side": "aria",
                           "notes": {"factos": 9, "voz": 7}, "score": 8.0, "errors": ["esqueceu a linha 🏠"],
                           "summary": "Boa, mas sem a linha."}]
    testlab.save_lab(service.folder, lab)
    draft_and_send_to(service, "t1", TEST_REF)
    ours = service.load(TEST_REF)["conversations"]["owner+cd1@example.com"]["sent_message_ids"][-1]
    read(service, [{"gmail_message_id": "t2", "from": [{"email": ACCOUNT}], "test": True,
                    "reply_to": [{"name": "Sergii", "email": "owner+cd1@example.com"}], "in_reply_to": ours,
                    "subject": "Re: resposta", "body_text": "Somos dois adultos e um gato."}])

    result = testlab.transcript(service, "2026-10-02T12:00:00+01:00")
    assert result["filename"] == f"teste-{TEST_REF}-2026-10-02.txt" and result["clients"] == 2
    text = result["text"]
    assert "1. Sergii Sviatokha · uk · owner+cd1@example.com" in text
    assert "Perfil escondido (o que a ARIA não sabe):\n  agregado: dois adultos\n  segredos: um gato" in text
    assert "ARIA\nOlá." in text  # our reply, in order after their first message
    assert "CLIENTE — por responder, na fila de Emails\nSomos dois adultos e um gato." in text
    assert "ARIA: 8.0 / 10 (factos 9 · voz 7) — Boa, mas sem a linha.\n    · esqueceu a linha 🏠" in text
    # a customer still without our first reply: their portal message, and the state says so
    assert "2. Ana Nova · owner+cd2@example.com" in text and "ainda sem resposta nossa" in text
    assert "Olá, posso visitar?" in text
    assert text.index("1. Sergii") < text.index("2. Ana Nova")


def test_the_test_property_has_a_tank_of_its_own_of_3_euros_in_the_painel(service):
    # 02/10: its API cost goes to its own tank (3 € unless filled otherwise), shown apart in Depósitos
    with_test_property(service)
    service.log("openai_usage", model="gpt-6-luna", prompt_tokens=10, completion_tokens=5, reference=TEST_REF, cost_usd=1.0)
    fuel = service.api_fuel(TEST_REF)
    assert (fuel["configured"], fuel["capacity_eur"], fuel["remaining_eur"]) == (True, 3.0, 2.0)
    metrics = service.metrics()
    assert TEST_REF not in [item["property_ref"] for item in metrics["properties"]]
    [tank] = metrics["test_tanks"]
    assert tank["property_ref"] == TEST_REF and tank["api_fuel"]["remaining_eur"] == 2.0
    assert tank["openai_usage"]["all_time"]["calls"] == 1 and metrics["openai_usage"]["unattributed"]["calls"] == 0
    assert service.fill_fuel(TEST_REF)["remaining_eur"] == 3.0  # filled: 3 € again, from zero
    service.log("openai_usage", model="gpt-6-luna", prompt_tokens=10, completion_tokens=5, reference=TEST_REF, cost_usd=3.5)
    with pytest.raises(ValueError, match="depósito da API de AP_teste1 está vazio"):
        service.require_fuel(TEST_REF)


class Never:
    """A random source that never adds the fractional extra customer."""
    def random(self):
        return 0.99


def test_a_round_answers_the_aria_and_the_consultant_in_character_and_only_once(service):
    with_test_property(service)
    read(service, [marked_notice("t1")])
    service.drafts([{"id": "t1", "reply_text": "Olá, pode dizer-nos quantas pessoas são?"}],
                   queue_of(service, TEST_REF)["revision"], TEST_REF)
    preview = service.preview(["t1"], TEST_REF)
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.send(preview["preview_token"], True, TEST_REF)
    ours = service.load(TEST_REF)["conversations"]["owner+cd1@example.com"]["sent_message_ids"][-1]
    lab = testlab.load_lab(service.folder)
    lab["clients"] = [{"number": 1, "name": "Sergii Sviatokha", "language": "uk", "address": "owner+cd1@example.com",
                       "phone": "900 000 001", "message": "Ainda está disponível?", "profile": {"agregado": "casal"},
                       "consultant_notice_id": "<copy@x>"}]
    lab["contest"] = {"on": True, "email": "consultor@example.com"}
    lab["new_percent"] = 0
    testlab.save_lab(service.folder, lab)
    from_consultant = [{"number": 1, "message_id": "<c1@x>", "subject": "Re: [consultor] Mensagem", "text": "Bom dia, quantos são?",
                        "at": "Tue, 29 Sep 2026 17:00:00 +0100"}]
    answers = {"respostas": [{"id": "a1", "responde": True, "texto": "Somos um casal.", "fim": False},
                             {"id": "c1", "responde": True, "texto": "Somos dois.", "fim": False}]}
    SMTP.sent = []
    with patch("backend.testlab.complete", return_value=(json.dumps(answers), {"prompt_tokens": 10, "completion_tokens": 5})) as ai, \
            patch("backend.testlab.consultant_messages", return_value=from_consultant), \
            patch("backend.testlab.openai_api_key", return_value="k"), patch("backend.testlab.app_password", return_value="p"), \
            patch("backend.testlab.smtplib.SMTP_SSL", SMTP):
        result = testlab.advance(service, "2026-09-29T18:00:00+01:00", Never())
        prompt = ai.call_args.args[2]
        assert ai.call_args.kwargs["effort"] == "none"  # their answers: no reasoning
        assert "effort" not in ai.call_args_list[0].kwargs  # the evaluator: the Oficina's effort
        again = testlab.advance(service, "2026-09-29T18:05:00+01:00", Never())
    assert (result["aria"], result["consultant"], result["silent"], result["new"]) == (["Sergii Sviatokha"], ["Sergii Sviatokha"], [], [])
    assert "Olá, pode dizer-nos quantas pessoas são?" in prompt and "Bom dia, quantos são?" in prompt and '"agregado": "casal"' in prompt
    to_aria, to_consultant = SMTP.sent
    assert (to_aria["To"], to_aria["X-ARIA-Teste"], to_aria["In-Reply-To"]) == (ACCOUNT, "1", ours)
    assert to_aria["Reply-To"] == "Sergii Sviatokha <owner+cd1@example.com>" and to_aria["Subject"].startswith("Re: ")
    assert (to_consultant["To"], to_consultant["X-ARIA-Teste"], to_consultant["In-Reply-To"]) == (
        "consultor@example.com", "consultor", "<c1@x>")
    # Each email of ours (and of the consultant) gets its round once: nothing new, nobody answers again
    assert again["aria"] == again["consultant"] == [] and len(SMTP.sent) == 2
    # Read back, the customer's answer is the next interaction of the test property
    item = {"gmail_message_id": "r1", "from": [{"name": "Sergii Sviatokha", "email": ACCOUNT}], "test": True,
            "reply_to": [{"name": "Sergii Sviatokha", "email": "owner+cd1@example.com"}], "in_reply_to": ours,
            "subject": to_aria["Subject"], "body_text": to_aria.get_content()}
    read(service, [item])
    [email] = queue_of(service, TEST_REF)["emails"]
    assert email["kind"] == "follow_up" and email["customer"]["message"] == "Somos um casal."


def test_a_silent_customer_and_one_whose_story_ended(service):
    with_test_property(service)
    read(service, [marked_notice("t1")])
    service.drafts([{"id": "t1", "reply_text": "Olá."}], queue_of(service, TEST_REF)["revision"], TEST_REF)
    preview = service.preview(["t1"], TEST_REF)
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.send(preview["preview_token"], True, TEST_REF)
    lab = testlab.load_lab(service.folder)
    lab["clients"] = [{"number": 1, "name": "Ana Teste", "address": "owner+cd1@example.com", "message": "Olá", "profile": {}}]
    lab["new_percent"] = 50  # one customer still in: 0,5 of a new one, never added by this random source
    testlab.save_lab(service.folder, lab)
    SMTP.sent = []
    answers = {"respostas": [{"id": "a1", "responde": False, "texto": "", "fim": True}]}
    with patch("backend.testlab.complete", return_value=(json.dumps(answers), {"prompt_tokens": 1, "completion_tokens": 1})), \
            patch("backend.testlab.openai_api_key", return_value="k"), patch("backend.testlab.app_password", return_value="p"), \
            patch("backend.testlab.smtplib.SMTP_SSL", SMTP):
        result = testlab.advance(service, "2026-09-29T18:00:00+01:00", Never())
    assert result["silent"] == ["Ana Teste (ARIA)"] and result["new"] == [] and SMTP.sent == []
    assert result["clients"][0]["ended"] is True


def test_a_test_customer_never_answers_the_after_visit_survey(service):
    thanks = "2026-09-29T17:00:00.100000+00:00"
    conversation = {"visit_check": {"attended": True, "thanks_sent_at": "2026-09-29T17:00:00.300000+00:00"},
                    "history": [{"who": "cliente", "text": "Obrigado"}, {"who": "nos", "text": "Inquérito…", "ts": thanks}]}
    assert testlab.is_survey(conversation)
    conversation["history"].append({"who": "nos", "text": "Pedido de documentos", "ts": "2026-09-30T10:00:00+00:00"})
    assert not testlab.is_survey(conversation)
    assert not testlab.is_survey({"history": [{"who": "nos", "text": "Olá", "ts": thanks}]})


def test_the_painel_never_counts_the_test_property_not_even_after_a_wipe(service):
    with_test_property(service)
    read(service, [marked_notice("t1")])
    draft_and_send_to(service, "t1", TEST_REF)
    read(service, [lead("r1")])
    draft_and_send_to(service, "r1", REF)
    service.log("read", received={"t1": "2026-09-29", "r1": "2026-09-29"})

    def painel():
        metrics = service.metrics(14)
        return ([item["property_ref"] for item in metrics["properties"]], sum(day["requests"] for day in metrics["by_day"]),
                sum(day["sent"] for day in metrics["by_day"]))

    assert painel() == ([REF], 1, 1)
    assert [page["property_ref"] for page in service.digest_view()["properties"]] == [REF]
    testlab.wipe(service)
    assert painel() == ([REF], 1, 1)
    # and once the test property itself is gone
    import shutil
    shutil.rmtree(service.folder / "properties" / TEST_REF)
    assert painel() == ([REF], 1, 1)


def draft_and_send_to(service, key, ref):
    service.drafts([{"id": key, "reply_text": "Olá."}], queue_of(service, ref)["revision"], ref)
    preview = service.preview([key], ref)
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.send(preview["preview_token"], True, ref)


def test_the_calls_keep_within_the_share_of_the_context_and_the_emails_per_call(service):
    from backend.api import plan_batches
    from backend.ai import reply_prompt
    for n in range(1, 5):
        read(service, [lead(str(n), reply_to=(f"c{n}@example.com",), body_email=f"c{n}@example.com")])
    current = queue_of(service, REF)
    ids = [email["id"] for email in current["emails"]]
    batches, biggest = plan_batches(current, ids, "", False, "gpt-4o", {"context_share": 50, "batch_emails": 3})
    assert [len(batch) for batch in batches] == [3, 1] and 0 < biggest < 50
    # a small window: half of it holds one email's prompt but not two, so each call takes one (never none)
    from backend.openai_client import estimate_tokens
    one, two = (estimate_tokens(reply_prompt(current, ids[:n])) for n in (1, 2))
    service.set_context("gpt-4o", one + two)
    batches, _ = plan_batches(current, ids, "", False, "gpt-4o", {"context_share": 50, "batch_emails": 5})
    assert [len(batch) for batch in batches] == [1, 1, 1, 1]
    ai = service.set_call_limits(40, 2)
    assert ai["limits"] == {"context_share": 40, "batch_emails": 2}
    assert next(model for model in ai["models"] if model["id"] == "gpt-4o")["context_known"] is True
    assert next(model for model in ai["models"] if model["id"] == "gpt-6-luna")["context_known"] is False
    with pytest.raises(ValueError):
        service.set_call_limits(95, 2)
    service.set_context("gpt-4o", 0)  # the default back


@pytest.fixture(autouse=True)
def table_context():
    yield
    from backend.openai_client import apply_context
    apply_context({})



def test_the_common_prompts_change_only_in_the_oficina_and_reach_the_instructions(service):
    from starlette.testclient import TestClient
    from backend.api import web_app
    client = TestClient(web_app(service.folder, "t"), base_url="http://127.0.0.1:8765")
    call = lambda path, body: client.post(path, json=body, headers={"X-Bot-Mail-Token": "t"})
    new = {"survey_reply": "Agradece só, em duas linhas.", "application_instructions": "Tom formal."}
    assert call("/api/prompts/common", {"prompts": new}).status_code == 400
    config = load_json(service.folder / "config.json", {})
    save_json(service.folder / "config.json", {**config, "admin": True})
    settings = call("/api/prompts/common", {"prompts": new}).json()
    assert settings["voice"]["survey_reply"] == "Agradece só, em duas linhas."
    instructions = queue_of(service, REF)["instructions"]
    assert "Resposta ao inquérito (emails marcados «resposta ao inquérito»): Agradece só, em duas linhas." in instructions
    assert "Tom formal." in instructions
    # Voz e estilo never changes a prompt, even when sent one
    voice = json.loads((service.folder / "voice.json").read_text(encoding="utf-8"))
    choices = {key: voice["style"][key]["selected"] for key in ("greeting", "languages", "closing")}
    call("/api/voice", {**choices, "signature": "Equipa", "survey_reply": "Outra coisa."})
    assert service.settings()["voice"]["survey_reply"] == "Agradece só, em duas linhas."


def test_the_test_property_has_its_row_by_property_but_never_counts_in_the_totals(service):
    # 04/10: «Por imóvel» shows it last, marked; the cards' totals and the ponto de situação leave it out
    with_test_property(service)
    read(service, [marked_notice("t1")])
    metrics = service.metrics()
    assert TEST_REF not in [item["property_ref"] for item in metrics["properties"]] and metrics["totals"]["pending"] == 0
    [row] = metrics["test_properties"]
    assert (row["property_ref"], row["test"], row["pending"]) == (TEST_REF, True, 1)
    assert "advertised_rent_eur" in row  # 04/10: the rent column, as for every property
    # 04/10: and enough for its panel in Imóveis (the instruments show for it too)
    assert {"customers", "visits_booked", "reply_hours_max", "ignored", "last_read_at"} <= set(row)
