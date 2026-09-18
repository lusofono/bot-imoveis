"""Single-owner OAuth provider. SDK handles discovery, DCR and S256 PKCE.

One process per replica. Persistent credentials/tokens survive restarts; pending
login transactions intentionally expire on restart. No email password in forms.
"""
import hashlib
import hmac
import html
import secrets
import time
from urllib.parse import urlencode, urlsplit
from mcp.server.auth.provider import (AccessToken, AuthorizationCode, AuthorizationParams,
    AuthorizeError, RefreshToken, RegistrationError, TokenError, construct_redirect_uri)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from .storage import load_json, save_json

SCOPE = "mail"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


class PersonalOAuth:
    def __init__(self, folder, public_url):
        self.folder = folder
        self.url = public_url.rstrip("/")
        self.resource = self.url + "/mcp"
        self.path = folder / "secrets" / "oauth.json"
        self.login_config = load_json(folder / "secrets" / "login.json", {})
        if not self.login_config.get("password_hash"):
            raise ValueError("Configura o acesso MCP com bot-mail setup-server antes de iniciar.")
        self.data = load_json(self.path, {"clients": {}, "codes": {}, "access": {}, "refresh": {}})
        self.pending = {}
        self.attempts = []

    def save(self):
        current = time.time()
        for kind in ("codes", "access", "refresh"):
            self.data[kind] = {k: v for k, v in self.data[kind].items()
                               if v.get("expires_at", 0) > current}
        save_json(self.path, self.data)

    async def get_client(self, client_id):
        value = self.data["clients"].get(client_id)
        return OAuthClientInformationFull.model_validate(value) if value else None

    async def register_client(self, client_info):
        allowed = self.login_config.get("redirect_uris", [])
        if not allowed or any(str(uri) not in allowed for uri in client_info.redirect_uris or []):
            raise RegistrationError("invalid_redirect_uri", "Adiciona o callback exato à lista permitida no setup-server.")
        if len(self.data["clients"]) >= 100:
            raise RegistrationError("invalid_client_metadata", "Limite de clientes atingido nesta réplica.")
        self.data["clients"][client_info.client_id] = client_info.model_dump(mode="json")
        self.save()

    async def authorize(self, client, params):
        if params.resource != self.resource:
            raise AuthorizeError("invalid_request", "Resource inválido.")
        if set(params.scopes or [SCOPE]) - {SCOPE}:
            raise AuthorizeError("invalid_scope")
        self.pending = {k: v for k, v in self.pending.items() if v["expires"] > time.time()}
        if len(self.pending) >= 100:
            raise AuthorizeError("temporarily_unavailable")
        ticket = secrets.token_urlsafe(32)
        self.pending[ticket] = {"client": client.client_id, "params": params,
                                "expires": time.time()+600, "csrf": secrets.token_urlsafe(32)}
        return self.url + "/login?" + urlencode({"ticket": ticket})

    async def login(self, request):
        headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
                   "Content-Security-Policy": "default-src 'none'; form-action 'self'; frame-ancestors 'none'",
                   "X-Content-Type-Options": "nosniff"}
        if request.method == "GET":
            ticket = request.query_params.get("ticket", "")
        else:
            form = await request.form()
            ticket = str(form.get("ticket", ""))
        entry = self.pending.get(ticket)
        if not entry or entry["expires"] < time.time():
            return PlainTextResponse("Ligação expirada. Volta a ligar no ChatGPT.", status_code=400, headers=headers)
        if request.method == "GET":
            response = HTMLResponse(
                '<!doctype html><html lang="pt"><meta charset="utf-8"><title>Ligar bot_mail</title>'
                '<h1>Ligar o teu bot_mail</h1><p>Autoriza este cliente a ler os teus emails, guardar rascunhos '
                'e enviar respostas quando deres essa instrução. Usa a password MCP desta réplica, não a do Gmail.</p>'
                f'<p>Destino: {html.escape(str(entry["params"].redirect_uri))}</p>'
                '<form method="post"><input type="hidden" name="ticket" value="' + html.escape(ticket) + '">'
                '<input type="hidden" name="csrf" value="' + entry["csrf"] + '">'
                '<label>Password MCP <input type="password" name="password" required autocomplete="current-password"></label>'
                '<button type="submit">Autorizar ligação</button></form></html>', headers=headers)
            response.set_cookie("bot_mail_login", ticket, httponly=True, secure=True, samesite="lax", max_age=600)
            return response
        if (request.cookies.get("bot_mail_login") != ticket
            or not hmac.compare_digest(str(form.get("csrf", "")), entry["csrf"])
            or request.headers.get("origin") not in (None, self.url)):
            return PlainTextResponse("Pedido inválido.", status_code=403, headers=headers)
        self.attempts = [stamp for stamp in self.attempts if stamp > time.time()-60]
        if len(self.attempts) >= 10:
            return PlainTextResponse("Aguarda um minuto antes de tentar novamente.", status_code=429, headers=headers)
        self.attempts.append(time.time())
        supplied = str(form.get("password", ""))
        if len(supplied) > 1024 or not hmac.compare_digest(
            password_hash(supplied, self.login_config["salt"]), self.login_config["password_hash"]):
            return PlainTextResponse("Password inválida. Volta atrás e tenta novamente.", status_code=403, headers=headers)
        self.pending.pop(ticket)
        params = entry["params"]
        code = secrets.token_urlsafe(32)
        auth = AuthorizationCode(code=code, client_id=entry["client"], scopes=params.scopes or [SCOPE],
            expires_at=time.time()+120, code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri, redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=self.resource, subject="owner")
        self.data["codes"][digest(code)] = auth.model_dump(mode="json")
        self.save()
        response = RedirectResponse(construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state),
                                    status_code=303, headers=headers)
        response.delete_cookie("bot_mail_login", secure=True, httponly=True, samesite="lax")
        return response

    async def load_authorization_code(self, client, authorization_code):
        value = self.data["codes"].get(digest(authorization_code))
        return AuthorizationCode.model_validate(value) if value else None

    def issue(self, client_id, scopes, resource, subject):
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.data["access"][digest(access)] = AccessToken(token="", client_id=client_id, scopes=scopes,
            expires_at=int(time.time())+3600, resource=resource, subject=subject).model_dump(mode="json")
        self.data["refresh"][digest(refresh)] = RefreshToken(token="", client_id=client_id, scopes=scopes,
            expires_at=int(time.time())+2592000, resource=resource, subject=subject).model_dump(mode="json")
        self.save()
        return OAuthToken(access_token=access, refresh_token=refresh, token_type="Bearer", expires_in=3600, scope=" ".join(scopes))

    async def exchange_authorization_code(self, client, authorization_code):
        value = self.data["codes"].pop(digest(authorization_code.code), None)
        if not value or value["expires_at"] < time.time() or value["client_id"] != client.client_id:
            raise TokenError("invalid_grant")
        return self.issue(client.client_id, authorization_code.scopes, authorization_code.resource, "owner")

    async def load_refresh_token(self, client, refresh_token):
        value = self.data["refresh"].get(digest(refresh_token))
        if not value or value["expires_at"] < time.time():
            return None
        return RefreshToken.model_validate({**value, "token": refresh_token})

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        value = self.data["refresh"].pop(digest(refresh_token.token), None)
        if not value or value["client_id"] != client.client_id or value["expires_at"] < time.time():
            raise TokenError("invalid_grant")
        if set(scopes) - set(value["scopes"]):
            raise TokenError("invalid_scope")
        return self.issue(client.client_id, scopes, refresh_token.resource, "owner")

    async def load_access_token(self, token):
        value = self.data["access"].get(digest(token))
        if not value or value["expires_at"] < time.time() or value.get("resource") != self.resource:
            return None
        return AccessToken.model_validate({**value, "token": token})

    async def revoke_token(self, token):
        for kind in ("access", "refresh"):
            self.data[kind] = {key: value for key, value in self.data[kind].items()
                               if value["client_id"] != token.client_id}
        self.save()
