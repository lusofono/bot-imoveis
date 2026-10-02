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
MODEL_DEFAULT = "gpt-4o-mini"  # 26/09: the default; the others are alternatives the owner picks in Voz e estilo
# USD per 1K tokens (input, output), OpenAI's own published rates when this was written. They change over time and the
# page always labels a cost built from this table "estimado": treat it as a rough guide, not an invoice.
# 27/09: six more, from developers.openai.com/api/docs/pricing that day, each tried once with a JSON call like the
# app's (all answered); gpt-6-astra the same way right after. gpt-5.6-terra's price may be promotional: check it again.
PRICE_PER_1K_USD = {"gpt-4o": (0.0025, 0.01), "gpt-4o-mini": (0.00015, 0.0006),
                    "gpt-4.1": (0.002, 0.008), "gpt-4.1-mini": (0.0004, 0.0016), "gpt-4.1-nano": (0.0001, 0.0004),
                    "gpt-5.6-terra": (0.002, 0.012), "gpt-6-sol": (0.002, 0.01), "gpt-6-luna": (0.0001, 0.0005),
                    "gpt-6-astra": (0.01, 0.05)}
PRICE_FALLBACK = PRICE_PER_1K_USD["gpt-4o"]
# The models the page offers: only those whose price is confirmed in the table above (the owner's rule, 26/09).
MODELS = tuple(PRICE_PER_1K_USD)
BUILTIN_PRICES = dict(PRICE_PER_1K_USD)
# 29/09: each model's context window, in tokens, as OpenAI announces it — only the ones known for sure; the rest take
# CONTEXT_FALLBACK until the Oficina says otherwise (config.json "model_context").
BUILTIN_CONTEXT = {"gpt-4o": 128000, "gpt-4o-mini": 128000, "gpt-4.1": 1047576, "gpt-4.1-mini": 1047576,
                   "gpt-4.1-nano": 1047576}
CONTEXT_FALLBACK = 128000
CONTEXT_TOKENS = dict(BUILTIN_CONTEXT)
CHARS_PER_TOKEN = 3.2  # a prudent estimate for Portuguese (accents, short words): more tokens than the real count


def estimate_tokens(text):
    """How many tokens a prompt will take, before sending it: a prudent estimate, never below the real count by much."""
    return int(len(str(text or "")) / CHARS_PER_TOKEN) + 1


def context_of(model):
    return CONTEXT_TOKENS.get(model, CONTEXT_FALLBACK)


def apply_context(overrides):
    CONTEXT_TOKENS.clear()
    CONTEXT_TOKENS.update(BUILTIN_CONTEXT)
    for model, tokens in (overrides or {}).items():
        if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens > 0:
            CONTEXT_TOKENS[str(model)] = tokens


def apply_prices(overrides):
    """29/09: the prices typed in the Oficina (config.json "token_prices", USD per 1M tokens) over the table above; a
    model only there becomes one more to choose. Every cost estimate reads the table, so they all follow."""
    PRICE_PER_1K_USD.clear()
    PRICE_PER_1K_USD.update(BUILTIN_PRICES)
    for model, price in (overrides or {}).items():
        try:
            PRICE_PER_1K_USD[str(model)] = (float(price["input_usd_per_1m"]) / 1000, float(price["output_usd_per_1m"]) / 1000)
        except (TypeError, KeyError, ValueError):
            continue  # a broken entry never stops the page: the table's own price stays


# 02/10: kept in the table (old costs stay right) but not offered: old and dear (gpt-4o, gpt-4.1), or above 3 € per
# 100 interactions (gpt-6-astra). The Oficina can show them again (config.json "hidden_models").
HIDDEN_DEFAULT = ("gpt-4o", "gpt-4.1", "gpt-6-astra")
HIDDEN = {"models": set(HIDDEN_DEFAULT)}


def apply_hidden(hidden):
    HIDDEN["models"] = set(HIDDEN_DEFAULT if hidden is None else hidden)


def models():
    """The models on offer now: the table's, with the Oficina's own, less the hidden ones."""
    return tuple(model for model in PRICE_PER_1K_USD if model not in HIDDEN["models"])


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
                              "Tenta noutra altura, ou escreve a resposta à mão no cartão.") from None
        raise OpenAIError(f"A OpenAI devolveu um erro ({exc.code}): {_message(exc)}") from None
    except urllib.error.URLError as exc:
        raise OpenAIError(f"Não consegui contactar a OpenAI: {exc.reason}. Verifica a ligação e tenta de novo.") from None
    except TimeoutError:
        raise OpenAIError("A OpenAI demorou demasiado tempo a responder. Tenta de novo.") from None


def check_key(key, timeout=15):
    """A cheap call (no completion, so no cost) that only confirms the key works."""
    _request(MODELS_URL, key, data=None, timeout=timeout)


# 02/10: how much the model reasons before writing (Oficina; config.json "reasoning_effort"). Without it, a reasoning
# model (gpt-5.x, gpt-6) used its own default and thought before every batch: slower, and those tokens are paid.
# "none" by default: the replies are short and the prompt carries every rule. Only the models that take it get it.
EFFORTS = ("none", "minimal", "low", "medium", "high")
EFFORT_DEFAULT = "low"  # 02/10: the owner's choice — «low» is enough for these replies
REASONING = {"effort": EFFORT_DEFAULT}


def apply_effort(effort):
    """The Oficina's choice; "" (or anything else) leaves each model its own default."""
    REASONING["effort"] = effort if effort in EFFORTS else (EFFORT_DEFAULT if effort is None else "")


def takes_effort(model):
    return str(model).startswith(("gpt-5", "gpt-6", "o1", "o3", "o4"))


def complete(key, model, prompt, timeout=90, json_mode=True, effort=None):
    """One completion: the prompt already carries every instruction, so a single user message is enough.

    json_mode: True for drafting replies (parsed back into structured drafts); False for a read-only
    summary the owner just reads, where forcing JSON would only get in the way.

    effort: this call's reasoning effort, over the Oficina's (02/10: the test customers' emails go with "none").

    Returns (text, usage): usage is {"prompt_tokens", "completion_tokens", "total_tokens"} exactly as
    OpenAI billed it — always exact, unlike the €/$ estimate built from it later.
    """
    data = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        data["response_format"] = {"type": "json_object"}
    effort = REASONING["effort"] if effort is None else effort
    if effort and takes_effort(model):
        data["reasoning_effort"] = effort
    try:
        body = _request(API_URL, key, data=data, timeout=timeout)
    except OpenAIError as exc:
        if "reasoning_effort" not in data or "reasoning" not in str(exc).lower():
            raise
        data.pop("reasoning_effort")  # a model (or value) that does not take it: once more, with its own default
        body = _request(API_URL, key, data=data, timeout=timeout)
    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise OpenAIError("A OpenAI devolveu uma resposta vazia ou inesperada.") from None
    if not text or not text.strip():
        raise OpenAIError("A OpenAI devolveu uma resposta vazia.")
    usage = body.get("usage") or {}
    return text, {"prompt_tokens": usage.get("prompt_tokens", 0), "completion_tokens": usage.get("completion_tokens", 0),
                 "total_tokens": usage.get("total_tokens", 0),
                 # 02/10: the hidden reasoning, part of the completion tokens (paid), to see what the effort changes
                 "reasoning_tokens": ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)}
