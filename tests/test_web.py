import json
from pathlib import Path
import re
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient
from backend.ai import parse_replies, short_id
from backend.api import DISPLAY_VERSION, web_app
from test_properties import CUSTOMER, REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

TOKEN = "test-token"


@pytest.fixture
def page(service):
    client = TestClient(web_app(service.folder, TOKEN), base_url="http://127.0.0.1:8765")
    def call(path, body=None):
        response = (client.get(path, headers={"X-Bot-Mail-Token": TOKEN}) if body is None
                    else client.post(path, json=body, headers={"X-Bot-Mail-Token": TOKEN}))
        return response.status_code, response.json()
    return client, call


def test_page_needs_the_start_link_and_the_api_needs_the_token(page):
    client, _ = page
    assert client.get("/").status_code == 403
    assert client.get("/?t=wrong").status_code == 403
    start = client.get(f"/?t={TOKEN}", follow_redirects=False)
    assert start.status_code == 303 and "httponly" in start.headers["set-cookie"].lower()
    html = client.get("/")
    assert html.status_code == 200 and TOKEN in html.text
    nonce = html.headers["content-security-policy"].split("'nonce-")[1].split("'")[0]
    assert f'<script nonce="{nonce}">' in html.text and "{{" not in html.text
    assert f"v{DISPLAY_VERSION}" in html.text  # "0." shows as "α.": pyproject.toml stays plain semver
    assert DISPLAY_VERSION.startswith("α.")  # this project is still 0.x
    assert client.get("/api/state").status_code == 403
    assert client.post("/api/send", json={"confirmed": True}, headers={"X-Bot-Mail-Token": "wrong"}).status_code == 403
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


def test_the_page_is_served_as_its_own_files(page):
    client, _ = page
    client.get(f"/?t={TOKEN}")
    html = client.get("/")
    policy = html.headers["content-security-policy"]
    nonce = policy.split("'nonce-")[1].split("'")[0]
    assert "style-src 'self'" in policy and "unsafe-inline" not in policy
    assert '<link rel="stylesheet" href="style.css">' in html.text
    assert f'<script nonce="{nonce}" src="app.js"></script>' in html.text
    script, style = client.get("/app.js"), client.get("/style.css")
    assert script.headers["content-type"].startswith("text/javascript") and "X-Bot-Mail-Token" in script.text
    assert style.headers["content-type"].startswith("text/css") and "--accent" in style.text
    # A rich theme keeps its own stylesheet in frontend/themes/, linked from the page and served as CSS.
    assert '<link rel="stylesheet" href="themes/racing.css">' in html.text
    racing = client.get("/themes/racing.css")
    assert racing.headers["content-type"].startswith("text/css") and ':root[data-theme="racing"]' in racing.text
    # Its label is generic, with no brand; the id stays "racing" so a choice saved in the browser survives.
    assert '<option value="racing">90\'s RacingCar</option>' in html.text
    assert not any("Ferrari" in served.text for served in (html, script, style, racing))
    # 90's Boat is its sibling: its own stylesheet, its option and its entry in THEMES.
    assert '<link rel="stylesheet" href="themes/boat.css">' in html.text
    assert '<option value="boat">90\'s Boat</option>' in html.text and "'boat'" in script.text
    boat = client.get("/themes/boat.css")
    assert boat.headers["content-type"].startswith("text/css") and ':root[data-theme="boat"]' in boat.text
    # A skin's Sons switch starts hidden and off: nothing plays until the owner turns it on.
    assert re.search(r'<button id="sound-toggle"[^>]*aria-pressed="false"[^>]*\bhidden\b', html.text)
    # The template itself, with its placeholders, is never served; nor is a theme that does not exist.
    assert client.get("/index.html").status_code == 404
    assert client.get("/themes/nada.css").status_code == 404


def test_a_skin_only_dresses_its_own_theme():
    # Every rule in frontend/themes/<id>.css starts with :root[data-theme="<id>"], so a rich theme can never
    # change how the plain themes, or the other skins, look. @keyframes steps are not selectors.
    for sheet in sorted((Path(__file__).resolve().parents[1] / "frontend" / "themes").glob("*.css")):
        css = re.sub(r"/\*.*?\*/", "", sheet.read_text(encoding="utf-8"), flags=re.S)
        prefix, depth, keyframes, start = f':root[data-theme="{sheet.stem}"]', 0, None, 0
        for i, char in enumerate(css):
            if char == "{":
                head = css[start:i].strip()
                if head.startswith("@keyframes"):
                    keyframes = depth
                elif not head.startswith("@") and keyframes is None:
                    parts, level, last = [], 0, 0
                    for j, c in enumerate(head):  # split on the commas outside :is(), :not()…
                        level += (c == "(") - (c == ")")
                        if c == "," and level == 0:
                            parts, last = parts + [head[last:j]], j + 1
                    for selector in parts + [head[last:]]:
                        assert selector.strip().startswith(prefix), f"{sheet.name}: {selector.strip()[:80]}"
                depth, start = depth + 1, i + 1
            elif char == "}":
                depth, start = depth - 1, i + 1
                if keyframes is not None and depth == keyframes:
                    keyframes = None
            elif char == ";" and depth == 0:
                start = i + 1


def test_skin_words_only_name_headings_the_page_has():
    # A skin's words replace headings marked data-word (or asked for with word()); a key with a typo would be
    # silently ignored, so every key of every skin must exist on the page.
    frontend = Path(__file__).resolve().parents[1] / "frontend"
    script = (frontend / "app.js").read_text(encoding="utf-8")
    known = set(re.findall(r'data-word="([\w.]+)"', (frontend / "index.html").read_text(encoding="utf-8")))
    known |= set(re.findall(r"word\('([\w.]+)'", script))
    blocks = re.findall(r"words: \{(.*?)\n\s*\},", script, flags=re.S)
    assert len(blocks) >= 2  # racing and boat
    for block in blocks:
        keys = re.findall(r"'([\w.]+)':", block)
        assert keys and set(keys) <= known, set(keys) - known


def test_copy_paste_flow_drafts_previews_and_sends(service, page):
    _, call = page
    read(service, [lead("1")])
    status, state = call("/api/state")
    [email] = state["properties"][0]["emails"]
    status, result = call("/api/prompt", {"property_ref": REF, "ids": ["1"], "extra": "Sê breve."})
    prompt = result["prompt"]
    for expected in (email["short_id"], "Bom dia, gostaria de visitar o imóvel.", "Sê breve.",
                     "Equipa APalace Imobiliária", '"respostas"'):
        assert expected in prompt
    assert CUSTOMER not in prompt and "900 000 001" not in prompt  # the model does not need them
    answer = ("Aqui estão:\n```json\n" + json.dumps({"respostas": [{"id": email["short_id"],
              "reply_text": "Cara Ana,\n\nObrigado pelo contacto.", "nota": "Confirma a data da visita."}]}) + "\n```")
    status, pasted = call("/api/paste", {"property_ref": REF, "text": answer})
    assert status == 200 and pasted["saved"] == 1 and pasted["notes"][0]["nota"] == "Confirma a data da visita."
    assert pasted["state"]["properties"][0]["emails"][0]["reply_text"].startswith("Cara Ana")
    status, preview = call("/api/preview", {"property_ref": REF, "ids": ["1"]})
    assert preview["replies"][0]["to"] == CUSTOMER
    status, refused = call("/api/send", {"property_ref": REF, "preview_token": preview["preview_token"]})
    assert status == 400 and "Confirma" in refused["error"]
    SMTP.sent = []
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        status, sent = call("/api/send", {"property_ref": REF, "preview_token": preview["preview_token"],
                                          "confirmed": True})
    assert sent["results"] == [{"id": "1", "status": "sent"}] and SMTP.sent[0]["To"] == CUSTOMER


def test_pasted_answers_must_match_the_queue(service, page):
    _, call = page
    read(service, [lead("1")])
    status, error = call("/api/paste", {"property_ref": REF, "text": "Não consigo ajudar."})
    assert status == 400 and "JSON" in error["error"]
    status, error = call("/api/paste", {"property_ref": REF, "text": '{"respostas": [{"id": "ffffffff", "reply_text": "x"}]}'})
    assert status == 400 and "ffffffff" in error["error"]
    queue = {"emails": [{"id": "1843212345678901234"}]}
    # Full IDs and the English key are accepted too; empty reply_text keeps only the note.
    replies, notes = parse_replies('[{"id": "1843212345678901234", "reply_text": " ", "nota": "Espera."}]', queue)
    assert (replies, notes) == ([], [{"id": "1843212345678901234", "nota": "Espera."}])
    replies, _ = parse_replies(json.dumps({"replies": [{"id": short_id("1843212345678901234"), "reply_text": "Olá"}]}), queue)
    assert replies == [{"id": "1843212345678901234", "reply_text": "Olá"}]


def test_property_from_a_listing_answer_keeps_the_safety_rules(service, page):
    _, call = page
    status, result = call("/api/property/prompt", {"listing_url": "https://www.idealista.pt/imovel/12345678/"})
    assert "https://www.idealista.pt/imovel/12345678/" in result["prompt"]
    answer = json.dumps({"reference": "AP_NOVO", "listing_id": "12345678", "listing_url": "https://www.idealista.pt/imovel/12345678/",
                         "advertiser": "Anunciante", "description": "Apartamento T2 na Rua Nova, Lisboa",
                         "advertised_rent_eur": "1.250 €", "facts": ["70 m²", "Mobilado"],
                         "sender": "x@evil.example", "never_reply_to": []})
    status, parsed = call("/api/property/parse", {"text": answer})
    fields = parsed["fields"]
    assert fields["advertised_rent_eur"] == 1250 and fields["sender"] is None  # never taken from pasted text
    status, saved = call("/api/property/save", {"fields": fields})
    assert status == 200 and saved["created"] and saved["reference"] == "AP_NOVO"
    folder = service.folder / "properties" / "AP_NOVO"
    profile = json.loads((folder / "profile.json").read_text(encoding="utf-8"))
    assert profile["match"]["from_address_equals"] == "reply@idealista.pt"
    assert profile["reply"]["never_reply_to"] == ["reply@idealista.pt", "owner@example.com"]
    assert "_knowledge" not in profile and "AP_NOVO" in profile["reply"]["prompts"]["general"]["text"]
    assert "- Mobilado" in (folder / "knowledge" / "anuncio.md").read_text(encoding="utf-8")
    assert (folder / "knowledge" / "imovel.md").exists()
    # The new property receives its own portal notices, and its facts reach the instructions.
    result = read(service, [lead("9", ref="AP_NOVO", listing="12345678")])
    queue = next(item for item in result["properties"] if item["property_ref"] == "AP_NOVO")
    assert queue["added"] == 1 and "Mobilado" in queue["instructions"]
    # The owner can type the prompts, including the 2nd interaction.
    status, settings = call("/api/property/prompts", {"reference": "AP_NOVO", "prompts": {
        "general": "Contexto do AP_NOVO.", "first": "Pede rendimentos.", "second": "Propõe uma visita."}})
    assert status == 200
    status, state = call("/api/state")
    queue = next(item for item in state["properties"] if item["property_ref"] == "AP_NOVO")
    assert "2.ª: Propõe uma visita." in queue["instructions"]
    status, error = call("/api/property/save", {"fields": {**fields, "reference": "../fora"}})
    assert status == 400 and not (service.folder / "fora").exists()


def test_voice_is_edited_on_the_page(service, page):
    _, call = page
    status, settings = call("/api/settings")
    assert settings["voice"]["greeting"]["selected"] == "formal" and "cordial" in settings["voice"]["greeting"]["options"]
    status, error = call("/api/voice", {"greeting": "inventada", "languages": "pt_en_fr", "closing": "formal", "signature": "X"})
    assert status == 400
    status, settings = call("/api/voice", {"greeting": "cordial", "languages": "pt_en_fr", "closing": "formal",
                                           "signature": "Equipa Teste"})
    assert settings["voice"]["greeting"]["selected"] == "cordial" and settings["voice"]["signature"] == "Equipa Teste"
    status, state = call("/api/state")
    assert "Equipa Teste" in state["properties"][0]["instructions"]


def test_starting_the_page_again_never_stops_another_program(tmp_path):
    from backend.api import stop_previous
    import os, subprocess, sys
    stop_previous(tmp_path)  # no earlier page: nothing to do
    other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        (tmp_path / ".page.pid").write_text(str(other.pid))
        stop_previous(tmp_path)  # a pid that is not this page is left alone
        assert other.poll() is None
        (tmp_path / ".page.pid").write_text(str(os.getpid()))
        stop_previous(tmp_path)  # and the page never stops itself
    finally:
        other.kill()


def test_property_photo_is_the_owners_file_and_needs_the_page(service, page):
    import base64
    from backend.demo import picture
    client, call = page
    as_data_url = lambda data: "data:image/png;base64," + base64.b64encode(data).decode()
    status, error = call("/api/property/photo", {"reference": REF, "image": as_data_url(b"not an image")})
    assert status == 400 and "não é uma fotografia" in error["error"]
    status, error = call("/api/property/photo", {"reference": "OUTRO", "image": as_data_url(picture((1, 2, 3), 4, 3))})
    assert status == 400 and "desconhecido" in error["error"]
    status, settings = call("/api/property/photo", {"reference": REF, "image": as_data_url(picture((1, 2, 3), 4, 3))})
    assert status == 200 and settings["properties"][0]["photo"] is True
    assert (service.folder / "properties" / REF / "foto.png").stat().st_mode & 0o077 == 0
    # An <img> cannot send the token header, so the photo needs the page's cookie.
    assert client.get(f"/photo/{REF}").status_code == 403
    client.get(f"/?t={TOKEN}")
    served = client.get(f"/photo/{REF}")
    assert served.status_code == 200 and served.headers["content-type"] == "image/png"
    assert client.get("/photo/..%2Fconfig.json").status_code == 404


def test_the_owner_adds_knowledge_while_reviewing_replies(service, page):
    _, call = page
    read(service, [lead("1")])
    status, known = call("/api/knowledge", {"property_ref": REF})
    assert status == 200 and (known["property"], known["agency"]) == ([], [])
    status, result = call("/api/knowledge/note", {"property_ref": REF, "scope": "property",
                                                  "text": "Não tem arrecadação,\n mas pode usar a garagem."})
    assert status == 200 and result["scope"] == "property"
    assert "Não tem arrecadação, mas pode usar a garagem." in result["state"]["properties"][0]["instructions"]
    [notes] = result["knowledge"]["property"]
    # The owner sees the date in the file; the assistant gets the note and the rule, never the comment.
    assert notes["file"] == "notas.md" and "valem estas" in notes["text"] and "<!--" not in notes["text"]
    assert (service.folder / "properties" / REF / "knowledge" / "notas.md").stat().st_mode & 0o077 == 0
    status, result = call("/api/knowledge/note", {"property_ref": REF, "scope": "agency", "text": "Visitas só por email."})
    assert "Visitas só por email." in result["knowledge"]["agency"][0]["text"]
    for bad in ({"property_ref": REF, "scope": "property", "text": "  "},
                {"property_ref": REF, "scope": "outro", "text": "x"},
                {"property_ref": "../fora", "scope": "property", "text": "x"}):
        assert call("/api/knowledge/note", bad)[0] == 400
    assert not (service.folder / "fora").exists()


def test_visits_and_knowledge_are_edited_on_the_page(service, page):
    from datetime import date, timedelta
    _, call = page
    day = (date.today() + timedelta(days=1)).isoformat()
    read(service, [lead("1")])
    draft_and_send(service, "1")
    status, data = call("/api/visits/candidates", {"property_ref": REF})
    assert status == 200 and [(c["email"], c["state"]) for c in data["customers"]] == [(CUSTOMER, "ok")]
    status, result = call("/api/visits/propose", {"property_ref": REF, "day": day, "start": "17:00", "end": "18:00",
                                                  "emails": [CUSTOMER]})
    assert status == 200 and result["created"] == 1
    [proposal] = [e for e in result["state"]["properties"][0]["emails"] if e.get("kind") == "visit_proposal"]
    assert proposal["interaction"] == 3 and proposal["visit_window"]["day"] == day

    # Knowledge (RAG) files are saved whole, in the property or for the whole agency; a bad name is refused.
    status, saved = call("/api/knowledge/save", {"scope": "property", "property_ref": REF, "file": "visitas.md",
                                                 "text": "# Visitas\n- Só presenciais."})
    assert status == 200 and any(f["file"] == "visitas.md" for f in saved["knowledge"]["files"]["property"])
    status, error = call("/api/knowledge/save", {"scope": "agency", "file": "../fora.md", "text": "x"})
    assert status == 400 and not (service.folder / "fora.md").exists()
    status, saved = call("/api/knowledge/save", {"scope": "agency", "file": "know-how.md",
                                                 "text": "# Know-how\n- Visitas presenciais."})
    assert status == 200 and "Visitas presenciais" in json.dumps(saved["knowledge"]["agency"], ensure_ascii=False)

    # Each read can look further back than the default.
    with patch("backend.service.app_password", return_value="fake"), patch(
            "backend.service.read_messages", return_value=([], 0, "INBOX")) as fetch:
        status, _ = call("/api/read", {"days": 30})
    assert status == 200 and fetch.call_args.args[3] == (date.today() - timedelta(days=30)).isoformat()


def test_the_contacts_csv_downloads_only_with_the_page_cookie(service, page):
    client, _ = page
    assert client.get("/contactos.csv").status_code == 403
    client.get(f"/?t={TOKEN}")
    read(service, [lead("1")])
    response = client.get("/contactos.csv")
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/csv")
    assert response.content.startswith(b"\xef\xbb\xbf") and CUSTOMER in response.text


def test_generate_calls_the_api_and_saves_drafts_exactly_like_pasting(service, page):
    _, call = page
    read(service, [lead("1")])
    status, result = call("/api/prompt", {"property_ref": REF, "ids": ["1"], "extra": ""})
    answer = json.dumps({"respostas": [{"id": short_id("1"), "reply_text": "Cara Ana,\n\nObrigado.",
                         "nota": "Confirma a data."}]})
    usage = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}
    with patch("backend.api.openai_api_key", return_value="sk-test"), \
         patch("backend.api.complete", return_value=(answer, usage)) as complete:
        status, generated = call("/api/prompt/generate", {"property_ref": REF, "ids": ["1"], "extra": "Sê breve."})
    assert status == 200 and generated["saved"] == 1 and generated["notes"][0]["nota"] == "Confirma a data."
    assert generated["state"]["properties"][0]["emails"][0]["reply_text"].startswith("Cara Ana")
    assert generated["tokens"] == usage
    prompt_sent = complete.call_args.args[2]
    assert "Sê breve." in prompt_sent and CUSTOMER not in prompt_sent  # same prompt as copy/paste, no contacts
    # Tokens (never the prompt or the answer) are logged for the dashboard's cost panel.
    events = [json.loads(line) for line in (service.folder / "logs" / "events.jsonl").read_text().splitlines()]
    usage_event = next(e for e in events if e["event"] == "openai_usage")
    assert usage_event["model"] == "gpt-4o" and usage_event["prompt_tokens"] == 100 and usage_event["cost_usd"] > 0

    # Without a key, the error tells the owner exactly what to do; ChatGPT copy/paste keeps working regardless.
    status, error = call("/api/prompt/generate", {"property_ref": REF, "ids": ["1"]})
    assert status == 400 and "mac/openai_key.command" in error["error"]


def test_generate_surfaces_an_openai_error_without_touching_the_queue(service, page):
    _, call = page
    read(service, [lead("1")])
    from backend.openai_client import OpenAIError
    with patch("backend.api.openai_api_key", return_value="sk-test"), \
         patch("backend.api.complete", side_effect=OpenAIError("Chave OpenAI inválida ou revogada.")):
        status, error = call("/api/prompt/generate", {"property_ref": REF, "ids": ["1"]})
    assert status == 400 and "inválida" in error["error"]
    assert call("/api/state")[1]["properties"][0]["emails"][0]["reply_text"] == ""


def test_visit_analysis_endpoints(service, page):
    from test_visits import customer
    _, call = page
    read(service, [customer("1", "a@example.com")])
    draft_and_send(service, "1", "Olá.")
    status, result = call("/api/visits/analysis-prompt", {"property_ref": REF})
    assert status == 200 and "não uses JSON" in result["prompt"] and CUSTOMER not in result["prompt"]

    status, error = call("/api/visits/analyze", {"property_ref": REF})
    assert status == 400 and "mac/openai_key.command" in error["error"]
    with patch("backend.service.openai_api_key", return_value="sk-test"), \
         patch("backend.service.complete", return_value=("Resumo.", {"prompt_tokens": 10, "completion_tokens": 5})):
        status, analyzed = call("/api/visits/analyze", {"property_ref": REF})
    assert status == 200 and analyzed["summary"] == "Resumo."


def test_each_property_s_reply_time_limit_is_set_on_the_page(service, page):
    _, call = page
    read(service, [lead("1")])
    status, result = call("/api/property/panel", {"property_ref": REF, "reply_hours_max": 8})
    assert status == 200 and result["panel"]["reply_hours_max"] == 8
    assert call("/api/metrics", {"days": 14})[1]["properties"][0]["reply_hours_max"] == 8
    for bad in ({"property_ref": REF, "reply_hours_max": 0}, {"property_ref": REF},
                {"property_ref": "../fora", "reply_hours_max": 8}):
        assert call("/api/property/panel", bad)[0] == 400


def test_each_property_s_api_tank_empties_with_its_spend_and_stops_its_api_until_refilled(service, page):
    from test_dashboard import log_event
    _, call = page
    read(service, [lead("1")])
    assert service.api_fuel(REF)["configured"] is False and service.api_fuel(REF)["empty"] is False  # no tank: no limit
    log_event(service, 1, event="openai_usage", reference=REF, cost_usd=3.0)  # before the fill: never counts
    status, filled = call("/api/fuel/fill", {"property_ref": REF, "capacity_eur": 1})
    assert status == 200 and filled["fuel"]["remaining_eur"] == 1 and not filled["fuel"]["reserve"]
    assert "usd_to_eur" not in filled["fuel"]  # 1 € = 1 US$ for this assistant: no rate anywhere
    answer = json.dumps({"respostas": [{"id": short_id("1"), "reply_text": "Cara Ana,\n\nObrigado."}]})
    with patch("backend.api.openai_api_key", return_value="sk-test"), \
         patch("backend.api.complete", return_value=(answer, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})), \
         patch("backend.api.estimate_cost_usd", return_value=0.95):  # 0,95 US$ spends 0,95 €
        status, generated = call("/api/prompt/generate", {"property_ref": REF, "ids": ["1"]})
        assert status == 200 and generated["fuel"]["spent_eur"] == 0.95 and generated["fuel"]["reserve"]
        assert call("/api/settings")[1]["properties"][0]["api_fuel"]["remaining_eur"] == 0.05
        status, _ = call("/api/prompt/generate", {"property_ref": REF, "ids": ["1"]})  # the last drop
        status, refused = call("/api/prompt/generate", {"property_ref": REF, "ids": ["1"]})
    assert status == 400 and f"depósito da API de {REF} está vazio" in refused["error"]
    with pytest.raises(ValueError, match="está vazio"):
        service.analyze_visits(REF)
    assert call("/api/fuel/fill", {"property_ref": REF, "capacity_eur": 5})[1]["fuel"]["empty"] is False  # back on
    for bad in ({"property_ref": REF, "capacity_eur": 0}, {"property_ref": REF, "capacity_eur": "cinco"},
                {"property_ref": "OUTRO", "capacity_eur": 5}):
        assert call("/api/fuel/fill", bad)[0] == 400


def test_the_visits_petrol_is_set_on_the_property_s_panel(service, page):
    _, call = page
    read(service, [lead("1")])
    status, result = call("/api/property/panel", {"property_ref": REF, "distance_km": "18", "l_per_100km": "6.5"})
    assert status == 200 and result["panel"] == {"reply_hours_max": 24, "distance_km": 18, "l_per_100km": 6.5}
    petrol = call("/api/metrics", {"days": 14})[1]["properties"][0]["petrol"]
    assert (petrol["distance_km"], petrol["l_per_100km"], petrol["trips"], petrol["litres"]) == (18, 6.5, 0, 0)
    for bad in ({"property_ref": REF, "distance_km": -1}, {"property_ref": REF, "l_per_100km": 90}):
        assert call("/api/property/panel", bad)[0] == 400


def test_the_active_switch_through_the_api(page):
    client, call = page
    status, result = call("/api/property/active", {"reference": REF, "active": False})
    assert status == 200 and result["settings"]["properties"][0]["active"] is False
    assert result["state"]["properties"][0]["inactive"] is True
    status, result = call("/api/property/active", {"reference": REF, "active": "sim"})
    assert status == 400
    status, result = call("/api/property/active", {"reference": REF, "active": True})
    assert result["settings"]["properties"][0]["active"] is True
