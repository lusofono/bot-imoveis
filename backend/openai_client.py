"""The OpenAI API: an alternative to copying the prompt into ChatGPT by hand.

Standard library only (urllib), like the rest of the project. Every other rule stays the same as the
copy/paste path: the prompt built by ai.reply_prompt is the only instruction, the customer's email is
data inside it, and the answer is parsed and saved as a draft by ai.parse_replies — never sent on its own.
"""
import json
import urllib.error
import urllib.request

API_URL = "https://api.openai.com/v1/chat/completions"
MODELS_URL = "https://api.openai.com/v1/models"
MODEL_DEFAULT = "gpt-4o"
# USD per 1K tokens, OpenAI's own published rates when this was written. They change over time and the
# page always labels a cost built from this table "estimado": treat it as a rough guide, not an invoice.
PRICE_PER_1K_USD = {"gpt-4o": (0.0025, 0.01), "gpt-4o-mini": (0.00015, 0.0006)}
PRICE_FALLBACK = PRICE_PER_1K_USD["gpt-4o"]


def estimate_cost_usd(model, prompt_tokens, completion_tokens):
    input_rate, output_rate = PRICE_PER_1K_USD.get(model, PRICE_FALLBACK)
    return (prompt_tokens or 0) / 1000 * input_rate + (completion_tokens or 0) / 1000 * output_rate


class OpenAIError(RuntimeError):
    pass


def _message(exc):
    try:
        body = json.loads(exc.read().decode("utf-8", "replace"))
        return (body.get("error") or {}).get("message") or str(exc)
    except (ValueError, AttributeError):
        return str(exc)


def _request(url, key, data=None, timeout=30):
    request = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                                     method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise OpenAIError("Chave OpenAI inválida ou revogada. Guarda-a de novo com mac/openai_key.command.") from None
        if exc.code == 429:
            raise OpenAIError("A OpenAI recusou o pedido (limite de pedidos ou sem crédito na conta). "
                              "Tenta noutra altura, ou usa Criar prompt/Copiar.") from None
        raise OpenAIError(f"A OpenAI devolveu um erro ({exc.code}): {_message(exc)}") from None
    except urllib.error.URLError as exc:
        raise OpenAIError(f"Não consegui contactar a OpenAI: {exc.reason}. Verifica a ligação e tenta de novo.") from None
    except TimeoutError:
        raise OpenAIError("A OpenAI demorou demasiado tempo a responder. Tenta de novo.") from None


def check_key(key, timeout=15):
    """A cheap call (no completion, so no cost) that only confirms the key works."""
    _request(MODELS_URL, key, data=None, timeout=timeout)


def complete(key, model, prompt, timeout=90, json_mode=True):
    """One completion: the prompt already carries every instruction, so a single user message is enough.

    json_mode: True for drafting replies (parsed back into structured drafts); False for a read-only
    summary the owner just reads, where forcing JSON would only get in the way.

    Returns (text, usage): usage is {"prompt_tokens", "completion_tokens", "total_tokens"} exactly as
    OpenAI billed it — always exact, unlike the €/$ estimate built from it later.
    """
    data = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        data["response_format"] = {"type": "json_object"}
    body = _request(API_URL, key, data=data, timeout=timeout)
    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise OpenAIError("A OpenAI devolveu uma resposta vazia ou inesperada.") from None
    if not text or not text.strip():
        raise OpenAIError("A OpenAI devolveu uma resposta vazia.")
    usage = body.get("usage") or {}
    return text, {"prompt_tokens": usage.get("prompt_tokens", 0), "completion_tokens": usage.get("completion_tokens", 0),
                 "total_tokens": usage.get("total_tokens", 0)}
