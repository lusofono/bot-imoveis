import asyncio
import base64
import hashlib
import re
import time
from urllib.parse import urlsplit, parse_qs
from starlette.testclient import TestClient
from bot_mail.server import http_app
from bot_mail.storage import save_json
from bot_mail.oauth import PersonalOAuth, password_hash

URL = "https://mail.example.com"
CALLBACK = "https://chatgpt.com/connector/oauth/test-connection"
PASSWORD = "a-long-test-password-only"


def fixture(folder):
    save_json(folder / "config.json", {"account": "owner@example.com"})
    save_json(folder / "secrets/login.json", {"salt": "aa"*16,
        "password_hash": password_hash(PASSWORD, "aa"*16), "redirect_uris": [CALLBACK]})


def test_oauth_pkce_and_authenticated_mcp(tmp_path):
    fixture(tmp_path)
    with TestClient(http_app(tmp_path, URL), base_url=URL) as http:
        response = http.post("/mcp", json={})
        assert response.status_code == 401
        assert "resource_metadata" in response.headers["www-authenticate"]
        metadata = http.get("/.well-known/oauth-protected-resource/mcp").json()
        assert metadata["resource"] == URL + "/mcp"
        auth = http.get("/.well-known/oauth-authorization-server").json()
        assert "S256" in auth["code_challenge_methods_supported"]
        client = http.post("/register", json={"redirect_uris": [CALLBACK], "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"], "scope": "mail"})
        assert client.status_code == 201, client.text
        client_id = client.json()["client_id"]
        verifier = "a"*64
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        response = http.get("/authorize", params={"client_id": client_id, "redirect_uri": CALLBACK,
            "response_type": "code", "code_challenge": challenge, "code_challenge_method": "S256",
            "scope": "mail", "state": "test-state", "resource": URL+"/mcp"}, follow_redirects=False)
        assert response.status_code == 302, response.text
        login = http.get(response.headers["location"])
        ticket = re.search(r'name="ticket" value="([^"]+)"', login.text)[1]
        csrf = re.search(r'name="csrf" value="([^"]+)"', login.text)[1]
        assert http.post("/login", data={"ticket": ticket, "csrf": "bad", "password": PASSWORD}).status_code == 403
        done = http.post("/login", data={"ticket": ticket, "csrf": csrf, "password": PASSWORD}, follow_redirects=False)
        assert done.status_code == 303, done.text
        args = parse_qs(urlsplit(done.headers["location"]).query)
        assert args["state"] == ["test-state"]
        payload = {"grant_type": "authorization_code", "client_id": client_id, "code": args["code"][0],
                   "redirect_uri": CALLBACK, "code_verifier": "wrong", "resource": URL+"/mcp"}
        assert http.post("/token", data=payload).status_code == 400
        payload["code_verifier"] = verifier
        token = http.post("/token", data=payload)
        assert token.status_code == 200, token.text
        assert http.post("/token", data=payload).status_code == 400
        headers = {"Authorization": "Bearer "+token.json()["access_token"], "Accept": "application/json, text/event-stream"}
        initialized = http.post("/mcp", headers=headers, json={"jsonrpc":"2.0", "id":1, "method":"initialize",
            "params":{"protocolVersion":"2025-03-26", "capabilities":{}, "clientInfo":{"name":"test", "version":"1"}}})
        assert initialized.status_code == 200, initialized.text
        tools = http.post("/mcp", headers=headers, json={"jsonrpc":"2.0", "id":2, "method":"tools/list"})
        assert {t["name"] for t in tools.json()["result"]["tools"]} == {"read_emails", "list_pending", "save_replies", "preview_send", "send_replies"}
        response = http.post("/mcp", headers=headers, json={"jsonrpc":"2.0", "id":3, "method":"tools/call", "params":{"name":"list_pending", "arguments":{}}})
        assert response.status_code == 200 and not response.json()["result"].get("isError"), response.text
        # Tokens and registration survive restart; another instance cannot use them.
        assert asyncio.run(PersonalOAuth(tmp_path, URL).load_access_token(token.json()["access_token"]))
        other = tmp_path / "other"
        fixture(other)
        assert asyncio.run(PersonalOAuth(other, URL).load_access_token(token.json()["access_token"])) is None
        refresh = {"grant_type":"refresh_token", "client_id":client_id, "refresh_token": token.json()["refresh_token"], "resource":URL+"/mcp"}
        renewed = http.post("/token", data=refresh)
        assert renewed.status_code == 200, renewed.text
        assert http.post("/token", data=refresh).status_code == 400
        assert http.post("/register", json={"redirect_uris": ["https://evil.example/callback"]}).status_code == 400
        assert http.get("/health", headers={"Host": "evil.example"}).status_code == 400
