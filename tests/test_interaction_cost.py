"""What 100 interactions cost with each model (27/09): this folder's own average, plus a margin, to quote a client."""
from test_properties import service  # noqa: F401 (service is a fixture)


def test_the_price_of_100_interactions_is_this_folders_average_plus_20_percent(service):
    before = service.ai_settings()
    assert before["cost_basis"]["interactions"] == 0 and all(model["per_100_usd"] is None for model in before["models"])
    service.log("openai_usage", model="gpt-4o", prompt_tokens=3000, completion_tokens=400, cost_usd=0.0115)
    service.log("openai_usage", model="gpt-4o-mini", prompt_tokens=1000, completion_tokens=200, cost_usd=0.0003)
    for kind in ("lead", "follow_up", "reminder", "visit_proposal"):
        service.log("send", message_id=kind, status="sent", kind=kind)
    service.log("send", message_id="gmail", status="sent", kind="direct")  # written by the owner in Gmail: not counted
    service.log("send", message_id="failed", status="error", kind="lead")  # did not go: not counted
    ai = service.ai_settings()
    basis = ai["cost_basis"]
    assert (basis["interactions"], basis["prompt_tokens"], basis["completion_tokens"]) == (4, 4000, 600)
    # 1000 tokens in and 150 out per interaction, plus 20%: 1200 and 180, at each model's price
    assert {model: basis["per_100_usd"][model] for model in ("gpt-4o", "gpt-4o-mini")} == {"gpt-4o": 0.48, "gpt-4o-mini": 0.0288}
    offered = {model["id"]: model["per_100_usd"] for model in ai["models"]}
    assert (offered["gpt-4o"], offered["gpt-4o-mini"]) == (0.48, 0.0288)
    # 27/09: the models whose price was confirmed that day are offered too, each with its own price per 100
    assert {"gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-5.6-terra", "gpt-6-sol", "gpt-6-luna", "gpt-6-astra"} <= set(offered)
    assert offered["gpt-6-luna"] < offered["gpt-4o-mini"] < offered["gpt-6-sol"]
    # quoted to a client in euros, at the rate of the day it was set
    assert basis["per_100_eur"] == {model: round(value / basis["usd_per_eur"], 4) for model, value in basis["per_100_usd"].items()}
    assert basis["per_100_eur"]["gpt-4o-mini"] < basis["per_100_usd"]["gpt-4o-mini"]


def test_the_wallet_counts_the_last_month_whatever_the_charts_period(service):
    import json
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch
    for tokens in (1000, 2000):
        service.log("openai_usage", model="gpt-4o-mini", prompt_tokens=tokens, completion_tokens=100, cost_usd=0.001)
    old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    with open(service.folder / "logs" / "events.jsonl", "a", encoding="utf-8") as stream:
        stream.write(json.dumps({"at": old, "event": "openai_usage", "model": "gpt-4o-mini", "prompt_tokens": 500,
                                 "completion_tokens": 50, "cost_usd": 0.0005}) + "\n")
    for days in (3, 90):
        with patch("backend.service.has_app_password", return_value=False):
            usage = service.metrics(days)["openai_usage"]
        assert (usage["all_time"]["calls"], usage["month"]["calls"]) == (3, 2)  # 40 days ago is out of the month
        assert usage["month"]["prompt_tokens"] == 3000
