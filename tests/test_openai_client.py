import json
import urllib.error
from unittest.mock import MagicMock, patch
import pytest
from backend.openai_client import OpenAIError, check_key, complete, estimate_cost_usd


def response(body):
    mock = MagicMock()
    mock.read.return_value = json.dumps(body).encode()
    mock.__enter__.return_value = mock
    return mock


def http_error(code, message):
    body = json.dumps({"error": {"message": message}}).encode()
    exc = urllib.error.HTTPError("https://api.openai.com/v1/chat/completions", code, message, {}, None)
    exc.read = lambda: body
    return exc


def test_complete_returns_the_message_text_and_usage_and_asks_for_json():
    reply = {"choices": [{"message": {"content": '{"respostas": []}'}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}}
    with patch("backend.openai_client.urllib.request.urlopen", return_value=response(reply)) as urlopen:
        text, usage = complete("sk-test", "gpt-4o", "o prompt")
    assert text == '{"respostas": []}'
    assert usage == {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}
    request = urlopen.call_args.args[0]
    assert request.get_header("Authorization") == "Bearer sk-test"
    body = json.loads(request.data)
    assert body["model"] == "gpt-4o" and body["messages"] == [{"role": "user", "content": "o prompt"}]
    assert body["response_format"] == {"type": "json_object"}


def test_complete_can_skip_json_mode_for_a_read_only_summary():
    reply = {"choices": [{"message": {"content": "Resumo em texto corrido."}}]}
    with patch("backend.openai_client.urllib.request.urlopen", return_value=response(reply)) as urlopen:
        text, _ = complete("sk-test", "gpt-4o", "prompt", json_mode=False)
    assert text == "Resumo em texto corrido."
    assert "response_format" not in json.loads(urlopen.call_args.args[0].data)


def test_complete_defaults_usage_to_zero_when_missing():
    with patch("backend.openai_client.urllib.request.urlopen",
              return_value=response({"choices": [{"message": {"content": "{}"}}]})):
        _, usage = complete("sk-test", "gpt-4o", "prompt")
    assert usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def test_estimate_cost_uses_the_model_rate_or_falls_back():
    assert estimate_cost_usd("gpt-4o", 1000, 1000) == pytest.approx(0.0025 + 0.01)
    assert estimate_cost_usd("gpt-4o-mini", 1000, 1000) == pytest.approx(0.00015 + 0.0006)
    assert estimate_cost_usd("unknown-model", 1000, 1000) == pytest.approx(0.0025 + 0.01)


def test_complete_raises_on_an_empty_answer():
    with patch("backend.openai_client.urllib.request.urlopen",
              return_value=response({"choices": [{"message": {"content": "  "}}]})):
        with pytest.raises(OpenAIError, match="vazia"):
            complete("sk-test", "gpt-4o", "prompt")
    with patch("backend.openai_client.urllib.request.urlopen", return_value=response({"choices": []})):
        with pytest.raises(OpenAIError, match="inesperada"):
            complete("sk-test", "gpt-4o", "prompt")


@pytest.mark.parametrize("code, match", [(401, "inválida ou revogada"), (429, "limite de pedidos"), (500, "erro \\(500\\)")])
def test_http_errors_get_a_clear_pt_message(code, match):
    with patch("backend.openai_client.urllib.request.urlopen", side_effect=http_error(code, "details")):
        with pytest.raises(OpenAIError, match=match):
            complete("sk-test", "gpt-4o", "prompt")


def test_network_and_timeout_errors_are_wrapped():
    with patch("backend.openai_client.urllib.request.urlopen", side_effect=urllib.error.URLError("no route")):
        with pytest.raises(OpenAIError, match="Não consegui contactar"):
            check_key("sk-test")
    with patch("backend.openai_client.urllib.request.urlopen", side_effect=TimeoutError()):
        with pytest.raises(OpenAIError, match="demorou demasiado"):
            check_key("sk-test")


def test_check_key_hits_the_models_endpoint_only_get_no_body():
    with patch("backend.openai_client.urllib.request.urlopen", return_value=response({"data": []})) as urlopen:
        check_key("sk-test")
    request = urlopen.call_args.args[0]
    assert request.full_url.endswith("/v1/models") and request.data is None and request.get_method() == "GET"
