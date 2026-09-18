"""The page for the workflow without MCP: ChatGPT is reached by copy and paste.

Two ways to run it:
- local (`bot-mail web`): 127.0.0.1 only. Each start creates a random token that the browser gets once
  from the printed link and then keeps in an HttpOnly cookie.
- hosted (`hosted_app`, e.g. cPanel «Setup Python App»): behind the password set with
  `bot-mail web-password`. The session is a signed cookie, so it works across several worker processes.
Either way every API call repeats a token in a header, so no other site can read the queue or send.
"""
import hashlib
import hmac
import os
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from starlette.routing import Route
from .credentials import password_hash
from .prompts import listing_prompt, parse_listing, parse_replies, reply_prompt, short_id
from .service import MailService
from .storage import load_json

PAGE = Path(__file__).with_name("web.html")
LOGIN = Path(__file__).with_name("web_login.html")
COOKIE = "bot_mail_web"
SESSION = "bot_mail_session"
SESSION_SECONDS = 12 * 3600


def same(supplied, token):
    return secrets.compare_digest(str(supplied or "").encode(), str(token or "").encode())


def ids_of(body):
    ids = body.get("ids")
    if not isinstance(ids, list) or not all(isinstance(value, str) for value in ids):
        raise ValueError("Seleciona os emails.")
    return ids


def session_key(folder, login):
    """A random secret kept on the server and bound to the password hash: a new password ends every session."""
    path = Path(folder) / "secrets" / "session_key"
    if not path.exists():
        path.parent.mkdir(mode=0o700, exist_ok=True)
        tmp = path.with_name(f".session_key.{secrets.token_hex(4)}")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(secrets.token_hex(32))
        try:
            os.link(tmp, path)  # atomic: the first worker process wins and the others read its key
        except FileExistsError:
            pass
        finally:
            tmp.unlink()
    return hashlib.sha256(path.read_text().strip().encode() + login["password_hash"].encode()).digest()


def hosted_app(folder):
    """The page on a hosting account. Without a page password it refuses to start: never an open page."""
    login = load_json(Path(folder) / "secrets" / "web.json", {})
    if not all(login.get(key) for key in ("public_url", "salt", "password_hash")):
        raise RuntimeError("Define a password da página: bot-mail --instance <pasta> web-password")
    return web_app(folder, login=login)


def web_app(folder, token=None, login=None):
    service = MailService(folder)
    hosted = login is not None
    if hosted:
        public = urlsplit(login["public_url"])
        base, origin, hosts = public.path.rstrip("/") + "/", f"{public.scheme}://{public.netloc}", [public.hostname]
        key, attempts = session_key(folder, login), []
    else:
        base, origin, hosts = "/", None, ["127.0.0.1", "localhost"]

    def sign(value):
        return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()

    def signed_in(request):
        """Hosted: the page token of a valid session cookie, else None."""
        cookie = request.cookies.get(SESSION, "")
        expires, _, mac = cookie.partition(".")
        if not expires.isdigit() or int(expires) < time.time() or not same(mac, sign(expires)):
            return None
        return sign("csrf:" + cookie)

    def state():
        try:
            data = service.pending()
        except ValueError as exc:
            # E.g. no profile yet or an incomplete voice: the settings tabs still work.
            return {"error": str(exc), "properties": []}
        queues = data.get("properties") or [{"property_ref": None, "revision": data["revision"], "instructions": "",
                                             "last_read_at": data.get("last_read_at"), "emails": data["emails"]}]
        for queue in queues:
            for email in queue["emails"]:
                email["short_id"] = short_id(email["id"])
        return {"account": data["account"], "error": None, "properties": queues}

    def queue(ref):
        current = state()
        if current["error"]:
            raise ValueError(current["error"])
        found = next((item for item in current["properties"] if item["property_ref"] == (ref or None)), None)
        if not found:
            raise ValueError("Imóvel desconhecido.")
        return found

    def read(body):
        result = service.read()
        current = state()
        current["added"] = sum(item.get("added", 0) for item in result.get("properties", [])) or result.get("added", 0)
        return current

    def prompt(body):
        return {"prompt": reply_prompt(queue(body.get("property_ref")), ids_of(body), str(body.get("extra") or ""))}

    def paste(body):
        current = queue(body.get("property_ref"))
        replies, notes = parse_replies(str(body.get("text") or ""), current)
        saved = service.drafts(replies, current["revision"], current["property_ref"])["saved"] if replies else 0
        return {"saved": saved, "notes": notes, "state": state()}

    def drafts(body):
        current = queue(body.get("property_ref"))
        replies = body.get("replies")
        if not isinstance(replies, list) or not all(
                isinstance(r, dict) and isinstance(r.get("id"), str) and isinstance(r.get("reply_text"), str)
                for r in replies):
            raise ValueError("Rascunhos inválidos.")
        service.drafts([{"id": r["id"], "reply_text": r["reply_text"]} for r in replies],
                       current["revision"], current["property_ref"])
        return state()

    def preview(body):
        return service.preview(ids_of(body), queue(body.get("property_ref"))["property_ref"])

    def send(body):
        if body.get("confirmed") is not True:
            raise ValueError("Confirma o envio na página.")
        return service.send(str(body.get("preview_token") or ""), True, body.get("property_ref") or None)

    def dismiss(body):
        current = queue(body.get("property_ref"))
        service.dismiss(ids_of(body), current["revision"], current["property_ref"])
        return state()

    def voice(body):
        service.save_voice(body)
        return service.settings()

    def property_prompt(body):
        url = str(body.get("listing_url") or "").strip()
        if urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
            raise ValueError("Indica o link do anúncio, começado por https://.")
        return {"prompt": listing_prompt(url)}

    def property_save(body):
        return {**service.save_property(body.get("fields") or {}), "settings": service.settings()}

    def property_prompts(body):
        service.save_prompts(str(body.get("reference") or ""), body.get("prompts") or {})
        return service.settings()

    # One operation at a time from this page: a second click waits instead of failing on the
    # file lock. Other processes (MCP, terminal, other workers) still meet the file lock.
    serial = threading.Lock()

    def one_at_a_time(handler, body):
        with serial:
            return handler(body)

    def foreign(request):
        return hosted and request.method == "POST" and request.headers.get("origin") not in (None, origin)

    def api(handler):
        async def endpoint(request):
            expected = signed_in(request) if hosted else token
            if not expected or not same(request.headers.get("x-bot-mail-token"), expected) or foreign(request):
                return JSONResponse({"error": "Sessão terminada: volta a abrir a página."}, 403)
            body = {}
            if request.method == "POST":
                try:
                    body = await request.json()
                except ValueError:
                    body = None
                if not isinstance(body, dict):
                    return JSONResponse({"error": "Pedido inválido."}, 400)
            try:
                return JSONResponse(await run_in_threadpool(one_at_a_time, handler, body))
            except Exception as exc:  # the owner's own page: show the reason instead of a blank error
                return JSONResponse({"error": str(exc) or type(exc).__name__}, 400)
        return endpoint

    def html(template, page_token):
        nonce = secrets.token_urlsafe(16)
        text = template.read_text(encoding="utf-8")
        for name, value in (("TOKEN", page_token), ("NONCE", nonce), ("BASE", base), ("HOSTED", str(hosted).lower())):
            text = text.replace("{{" + name + "}}", value)
        return HTMLResponse(text, headers={
            "Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; "
                                       "connect-src 'self'; img-src 'self' data:; form-action 'none'; "
                                       "frame-ancestors 'none'; base-uri 'self'"})

    async def page(request):
        if hosted:
            current = signed_in(request)
            return html(PAGE, current) if current else html(LOGIN, "")
        supplied = request.query_params.get("t")
        if supplied is not None:
            if not same(supplied, token):
                return PlainTextResponse("Link inválido ou antigo: usa o que o terminal mostrou neste arranque.", 403)
            response = RedirectResponse("/", 303)  # keeps the token out of the address bar and history
            response.set_cookie(COOKIE, token, httponly=True, samesite="strict")
            return response
        if not same(request.cookies.get(COOKIE), token):
            return PlainTextResponse("Abre o link mostrado no terminal ao iniciar a página.", 403)
        return html(PAGE, token)

    async def sign_in(request):
        now = time.time()
        attempts[:] = [stamp for stamp in attempts if stamp > now - 60]
        if foreign(request):
            return JSONResponse({"error": "Pedido inválido."}, 403)
        if len(attempts) >= 10:
            return JSONResponse({"error": "Demasiadas tentativas. Espera um minuto."}, 429)
        attempts.append(now)
        try:
            body = await request.json()
        except ValueError:
            body = None
        supplied = str(body.get("password") or "") if isinstance(body, dict) else ""
        if not supplied or len(supplied) > 1024 or not same(
                await run_in_threadpool(password_hash, supplied, login["salt"]), login["password_hash"]):
            return JSONResponse({"error": "Password errada."}, 403)
        expires = str(int(now) + SESSION_SECONDS)
        response = JSONResponse({"ok": True})
        response.set_cookie(SESSION, f"{expires}.{sign(expires)}", max_age=SESSION_SECONDS, path=base,
                            httponly=True, secure=True, samesite="strict")
        return response

    async def sign_out(request):
        response = JSONResponse({"ok": True})
        response.delete_cookie(SESSION, path=base, httponly=True, secure=True, samesite="strict")
        return response

    handlers = {"state": ("GET", lambda body: state()), "read": ("POST", read), "prompt": ("POST", prompt),
                "paste": ("POST", paste), "drafts": ("POST", drafts), "preview": ("POST", preview),
                "send": ("POST", send), "dismiss": ("POST", dismiss),
                "settings": ("GET", lambda body: service.settings()), "voice": ("POST", voice),
                "property/prompt": ("POST", property_prompt),
                "property/parse": ("POST", lambda body: {"fields": parse_listing(str(body.get("text") or ""))}),
                "property/save": ("POST", property_save), "property/prompts": ("POST", property_prompts)}
    routes = [Route("/", page)] + [Route(f"/api/{name}", api(handler), methods=[method])
                                   for name, (method, handler) in handlers.items()]
    if hosted:
        routes += [Route("/login", sign_in, methods=["POST"]), Route("/logout", sign_out, methods=["POST"])]
    app = Starlette(routes=routes)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    return app


def serve(folder, port=8765, open_browser=True):
    import uvicorn
    import webbrowser
    token = secrets.token_urlsafe(24)
    url = f"http://127.0.0.1:{port}/?t={token}"
    print(f"Página do bot_mail: {url}\nO link muda a cada arranque. Ctrl+C para parar.", flush=True)
    if open_browser:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    uvicorn.run(web_app(folder, token), host="127.0.0.1", port=port, access_log=False, log_level="warning")
