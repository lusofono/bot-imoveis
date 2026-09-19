"""The local page: the workflow without MCP, where ChatGPT is reached by copy and paste.

It runs on 127.0.0.1 only. Each start creates a random token that the browser gets once from the
printed link and then keeps in an HttpOnly cookie; every API call repeats it in a header, so no other
site can read the queue or send. The page itself is in frontend/ and only talks to this API.
The hosted mode (a login on a server) is paused; it returns with AWS.
"""
import secrets
import threading
from pathlib import Path
from urllib.parse import urlsplit
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from starlette.routing import Route
from .ai import listing_prompt, parse_listing, parse_replies, reply_prompt, short_id
from .service import MailService

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
COOKIE = "bot_mail_web"
# The page's own files. index.html is only served at "/", with the token written into it.
ASSETS = {"app.js": "text/javascript", "style.css": "text/css"}
HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


def same(supplied, token):
    return secrets.compare_digest(str(supplied or "").encode(), str(token or "").encode())


def ids_of(body):
    ids = body.get("ids")
    if not isinstance(ids, list) or not all(isinstance(value, str) for value in ids):
        raise ValueError("Seleciona os emails.")
    return ids


def web_app(folder, token):
    service = MailService(folder)

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
    # file lock. Other processes (MCP, terminal) still meet the file lock.
    serial = threading.Lock()

    def one_at_a_time(handler, body):
        with serial:
            return handler(body)

    def api(handler):
        async def endpoint(request):
            if not token or not same(request.headers.get("x-bot-mail-token"), token):
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

    async def page(request):
        supplied = request.query_params.get("t")
        if supplied is not None:
            if not same(supplied, token):
                return PlainTextResponse("Link inválido ou antigo: usa o que o terminal mostrou neste arranque.", 403)
            response = RedirectResponse("/", 303)  # keeps the token out of the address bar and history
            response.set_cookie(COOKIE, token, httponly=True, samesite="strict")
            return response
        if not same(request.cookies.get(COOKIE), token):
            return PlainTextResponse("Abre o link mostrado no terminal ao iniciar a página.", 403)
        nonce = secrets.token_urlsafe(16)
        text = (FRONTEND / "index.html").read_text(encoding="utf-8")
        for name, value in (("TOKEN", token), ("NONCE", nonce)):
            text = text.replace("{{" + name + "}}", value)
        return HTMLResponse(text, headers={
            **HEADERS, "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'self'; "
                                       "connect-src 'self'; img-src 'self' data:; form-action 'none'; "
                                       "frame-ancestors 'none'; base-uri 'self'"})

    def asset(name):
        async def endpoint(request):
            return Response((FRONTEND / name).read_bytes(), media_type=ASSETS[name], headers=HEADERS)
        return endpoint

    handlers = {"state": ("GET", lambda body: state()), "read": ("POST", read), "prompt": ("POST", prompt),
                "paste": ("POST", paste), "drafts": ("POST", drafts), "preview": ("POST", preview),
                "send": ("POST", send), "dismiss": ("POST", dismiss),
                "settings": ("GET", lambda body: service.settings()), "voice": ("POST", voice),
                "property/prompt": ("POST", property_prompt),
                "property/parse": ("POST", lambda body: {"fields": parse_listing(str(body.get("text") or ""))}),
                "property/save": ("POST", property_save), "property/prompts": ("POST", property_prompts)}
    routes = ([Route("/", page)] + [Route(f"/{name}", asset(name)) for name in ASSETS]
              + [Route(f"/api/{name}", api(handler), methods=[method]) for name, (method, handler) in handlers.items()])
    app = Starlette(routes=routes)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
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
