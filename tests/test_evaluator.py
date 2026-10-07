"""The evaluator (30/09): marks on fixed criteria and the mistakes quoted — for the real drafts (the reviewer) and for
the test platform's rounds (the ARIA and the consultant, knowing each customer's hidden profile)."""
import json
from unittest.mock import patch
import pytest
from backend import testlab
from backend.evaluator import CRITERIA, averages, evaluation_prompt, parse_evaluations
from backend.openai_client import apply_context, apply_prices
from backend.store import load_json, save_json
from test_properties import REF, SMTP, lead, read, service  # noqa: F401 (service is a fixture)
from test_testlab import ACCOUNT, TEST_REF, marked_notice, queue_of, with_test_property

USAGE = {"prompt_tokens": 100, "completion_tokens": 20}


@pytest.fixture(autouse=True)
def tables():
    yield
    apply_prices({})
    apply_context({})


def marks(ids, score=8, errors=()):
    return json.dumps({"avaliacoes": [{"id": key, "notas": {name: score for name in CRITERIA}, "erros": list(errors),
                                       "resumo": "Clara e correta."} for key in ids]})


def test_the_marks_are_read_bounded_and_averaged():
    text = json.dumps({"avaliacoes": [{"id": "a", "notas": {"factos": 12, "voz": 7, "avanco": "x"},
                                       "erros": ["  volta a perguntar o agregado  ", ""], "resumo": "ok"},
                                      {"id": "fora", "notas": {"factos": 1}}]})
    found = parse_evaluations(text, ["a"])
    assert set(found) == {"a"} and found["a"]["notes"] == {"factos": 10.0, "voz": 7.0} and found["a"]["score"] == 8.5
    assert found["a"]["errors"] == ["volta a perguntar o agregado"]
    assert averages([found["a"], {**found["a"], "score": 6.5}])["score"] == 7.5
    prompt = evaluation_prompt("REGRAS DO IMÓVEL", [{"id": "a", "turns": [{"who": "cliente", "text": "Tem garagem?"}],
                                                     "reply": "Tem.", "profile": {"segredos": "um cão"}}])
    assert "REGRAS DO IMÓVEL" in prompt and "Tem garagem?" in prompt and "um cão" in prompt and '"regras": 0' in prompt
    assert "um cão" not in evaluation_prompt("x", [{"id": "a", "reply": "r", "profile": {"segredos": "um cão"}}], hidden=False)


def test_the_reviewer_marks_the_real_drafts_while_their_text_is_the_one_read(service):
    read(service, [lead("1")])
    service.drafts([{"id": "1", "reply_text": "Cara Ana, agradecemos o seu contacto. A visita pode ser ao fim da tarde."}], queue_of(service, REF)["revision"], REF)
    with patch("backend.service.complete", return_value=(marks(["1"], 6, ["não responde à pergunta da hora"]), USAGE)) as ai, \
            patch("backend.service.openai_api_key", return_value="k"):
        result = service.review_drafts(REF, ["1"])
    assert result["reviewed"] == 1 and ai.call_args.args[1] == "gpt-6-sol"  # the evaluator's model, stronger by default
    assert "A visita pode ser ao fim da tarde." in ai.call_args.args[2] and "Bom dia, gostaria de visitar o imóvel." in ai.call_args.args[2]
    [email] = queue_of(service, REF)["emails"]
    assert email["review"]["score"] == 6 and email["review"]["errors"] == ["não responde à pergunta da hora"]
    assert email["review_fresh"] is True
    service.drafts([{"id": "1", "reply_text": "Cara Ana, agradecemos. A visita fica às 18h, como pediu."}],
                   queue_of(service, REF)["revision"], REF)
    assert queue_of(service, REF)["emails"][0]["review_fresh"] is False  # another text: the marks no longer hold
    ai = service.set_reviewer("gpt-4o-mini", False)
    assert ai["reviewer"] == {"model": "gpt-4o-mini", "auto": False}


def test_generating_reviews_the_new_drafts_when_the_reviewer_is_on(service):
    from starlette.testclient import TestClient
    from backend.ai import short_id
    from backend.api import web_app
    client = TestClient(web_app(service.folder, "t"), base_url="http://127.0.0.1:8765")
    assert service.reviewer_settings()["auto"] is False  # 02/10: off by default, the owner runs it when he wants
    service.set_reviewer("gpt-6-sol", True)
    read(service, [lead("1")])
    draft = json.dumps({"respostas": [{"id": short_id("1"), "reply_text": "Cara Ana, agradecemos o seu contacto. A visita pode ser ao fim da tarde."}]})
    with patch("backend.api.complete", return_value=(draft, USAGE)), patch("backend.api.openai_api_key", return_value="k"), \
            patch("backend.service.complete", return_value=(marks(["1"], 9), USAGE)), \
            patch("backend.service.openai_api_key", return_value="k"):
        result = client.post("/api/prompt/generate", json={"property_ref": REF, "ids": ["1"]},
                             headers={"X-Bot-Mail-Token": "t"}).json()
    assert result["saved"] == 1 and result["reviewed"] == 1 and result["review_error"] is None
    assert result["state"]["properties"][0]["emails"][0]["review"]["score"] == 9


def test_a_round_marks_the_aria_and_the_consultant_before_the_customers_answer(service):
    with_test_property(service)
    read(service, [marked_notice("t1")])
    service.drafts([{"id": "t1", "reply_text": "Olá, quantos são?"}], queue_of(service, TEST_REF)["revision"], TEST_REF)
    preview = service.preview(["t1"], TEST_REF)
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.send(preview["preview_token"], True, TEST_REF)
    lab = testlab.load_lab(service.folder)
    lab["clients"] = [{"number": 1, "name": "Sergii Sviatokha", "address": "owner+cd1@example.com", "message": "Olá",
                       "profile": {"agregado": "casal"}, "consultant_notice_id": "<copy@x>"}]
    lab["contest"], lab["new_percent"] = {"on": True, "email": "consultor@example.com"}, 0
    testlab.save_lab(service.folder, lab)
    consultant = [{"number": 1, "message_id": "<c1@x>", "subject": "Re: x", "text": "Bom dia! Tem animais?",
                   "at": "Tue, 29 Sep 2026 17:00:00 +0100"}]
    replies = json.dumps({"respostas": [{"id": "a1", "responde": False}, {"id": "c1", "responde": False}]})
    calls = [(marks(["a1", "c1"], 7, ["pergunta o que não é preciso"]), USAGE), (replies, USAGE)]
    with patch("backend.testlab.complete", side_effect=calls) as ai, \
            patch("backend.testlab.consultant_messages", return_value=consultant), \
            patch("backend.testlab.openai_api_key", return_value="k"), patch("backend.testlab.app_password", return_value="p"), \
            patch("backend.testlab.smtplib.SMTP_SSL", SMTP):
        result = testlab.advance(service, "2026-09-30T10:00:00+01:00", type("Never", (), {"random": lambda self: .99})())
    judged = ai.call_args_list[0].args
    assert judged[1] == "gpt-6-sol" and '"agregado": "casal"' in judged[2].replace("'", '"') and "Bom dia! Tem animais?" in judged[2]
    assert result["evaluated"] == 2
    report = result["evaluation"]
    assert report["aria"]["score"] == 7 and report["consultant"]["score"] == 7
    assert {item["side"] for item in report["last"]} == {"aria", "consultant"}
    assert report["last"][0]["errors"] == ["pergunta o que não é preciso"]


def test_a_draft_too_short_is_never_reviewed(service):
    read(service, [lead("1")])
    service.drafts([{"id": "1", "reply_text": "pdf"}], queue_of(service, REF)["revision"], REF)
    with patch("backend.service.complete") as ai, patch("backend.service.openai_api_key", return_value="k"):
        assert service.review_drafts(REF, ["1"]) == {"reviewed": 0, "cost_usd": 0.0}
    ai.assert_not_called()
    assert "SÓ o texto da «Resposta a avaliar»" in evaluation_prompt("x", [{"id": "a", "reply": "r"}])


def test_the_calls_go_at_the_same_time_in_order_and_one_error_never_loses_the_others():
    import threading
    import time
    from backend.api import run_parallel
    seen = set()

    def call(item):
        seen.add(threading.get_ident())
        time.sleep(0.05)
        if item == "erro":
            raise ValueError("falhou")
        return item.upper()

    started = time.monotonic()
    outcomes = run_parallel(call, ["a", "erro", "c", "d"])
    assert outcomes[0] == "A" and isinstance(outcomes[1], ValueError) and outcomes[2:] == ["C", "D"]
    assert time.monotonic() - started < 0.15 and len(seen) > 1  # together, not 4 × 50 ms one after the other



def test_the_program_signs_under_the_closing_never_twice():
    from backend.ai import sign
    assert sign("Cara Ana,\n\nObrigado.\n\nCom os melhores cumprimentos,", "Equipa X\nTel. 900") == \
        "Cara Ana,\n\nObrigado.\n\nCom os melhores cumprimentos,\nEquipa X\nTel. 900"
    # the AI signed anyway: its copy goes, the voice's stays
    assert sign("Olá.\n\nCumprimentos,\nEquipa X\n", "Equipa X\nTel. 900").endswith("Cumprimentos,\nEquipa X\nTel. 900")
    assert sign("", "Equipa X") == "" and sign("Olá.", "") == "Olá."


def test_the_owners_parts_come_in_portuguese_whatever_the_customers_language():
    # 02/10: the note and the file (for the owner) in pt-PT; only the reply in the customer's language
    from backend.ai import REPLY_FORMAT
    assert "em português de Portugal, seja qual for\na língua do cliente" in REPLY_FORMAT
    assert "português de Portugal, seja qual for a língua da conversa" in evaluation_prompt("", [])
