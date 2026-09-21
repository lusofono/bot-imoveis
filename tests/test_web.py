import json
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient
from backend.ai import parse_replies, short_id
from backend.api import web_app
from test_properties import CUSTOMER, REF, SMTP, lead, read, service  # noqa: F401 (service is a fixture)

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
    assert client.get("/api/state").status_code == 403
    assert client.post("/api/send", json={"confirmed": True}, headers={"X-Bot-Mail-Token": "wrong"}).status_code == 403
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


def test_the_page_is_served_as_its_three_files(page):
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
    # The template itself, with its placeholders, is never served.
    assert client.get("/index.html").status_code == 404


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
