"""The local page: the workflow without MCP, where ChatGPT is reached by copy and paste — or, optionally,
by the OpenAI API, as an alternative that skips the copy/paste but still only produces drafts.

It runs on 127.0.0.1 only. Each start creates a random token that the browser gets once from the
printed link and then keeps in an HttpOnly cookie; every API call repeats it in a header, so no other
site can read the queue or send. The page itself is in frontend/ and only talks to this API.
The hosted mode (a login on a server) is paused; it returns with AWS.
"""
import os
import secrets
import signal
import subprocess
import threading
import time
import tomllib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from starlette.routing import Route
from .ai import listing_prompt, parse_listing, parse_replies, parse_visits, reply_prompt, short_id
from .openai_client import MODEL_DEFAULT, complete, estimate_cost_usd
from .secrets import openai_api_key
from .service import MailService

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
COOKIE = "bot_mail_web"
# The page's own files. index.html is only served at "/", with the token written into it. A rich theme (a
# "skin": 90's RacingCar now, more to come) keeps its stylesheet in frontend/themes/, listed once at start.
ASSETS = {"app.js": "text/javascript", "style.css": "text/css",
          **{f"themes/{sheet.name}": "text/css" for sheet in sorted((FRONTEND / "themes").glob("*.css"))}}
HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
# pyproject.toml is the one place the version is written; CHANGELOG.md logs what changed at each one.
VERSION = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())["project"]["version"]
# pyproject.toml itself must stay a plain PEP 440 version (setuptools/pip parse it); the "0." that means
# "not even 1.0 yet" is shown instead as "α." wherever a person reads it, so it reads as alpha at a glance.
DISPLAY_VERSION = VERSION.replace("0.", "α.", 1) if VERSION.startswith("0.") else VERSION


def same(supplied, token):
    return secrets.compare_digest(str(supplied or "").encode(), str(token or "").encode())


def ids_of(body):
    ids = body.get("ids")
    if not isinstance(ids, list) or not all(isinstance(value, str) for value in ids):
        raise ValueError("Seleciona os emails.")
    return ids


def web_app(folder, token):
    """The page and its API for one data folder; every API call must carry this start's token."""
    service = MailService(folder)
    # When this process started running this code — not a compiled build, but the closest thing to one here.
    build_at = datetime.now().astimezone().strftime("%d/%m/%Y, %H:%M")

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
        result = service.read(body.get("days"))
        current = state()
        current["added"] = sum(item.get("added", 0) for item in result.get("properties", [])) or result.get("added", 0)
        current["direct"] = result.get("direct", 0)
        return current

    def prompt(body):
        return {"prompt": reply_prompt(queue(body.get("property_ref")), ids_of(body), str(body.get("extra") or ""))}

    def save_drafts_from(current, text):
        # Shared by "paste" (the human's copy from ChatGPT) and "generate" (the OpenAI API): same parsing,
        # same safety checks, same drafts-only save. Only where the text comes from differs.
        replies, notes = parse_replies(text, current)
        visits = parse_visits(text, current)
        saved = 0
        if replies or visits:
            saved = service.drafts(replies, current["revision"], current["property_ref"], visits)["saved"]
        return {"saved": saved, "notes": notes, "visits": len(visits), "state": state()}

    def paste(body):
        return save_drafts_from(queue(body.get("property_ref")), str(body.get("text") or ""))

    def generate(body):
        # The alternative to steps 02+03 by hand: the same prompt, answered by the OpenAI API instead of
        # a human pasting it into ChatGPT. Everything after that — parsing, drafts, preview, send — is
        # identical and needs the same review and confirmation before anything goes out.
        current = queue(body.get("property_ref"))
        service.require_fuel(current["property_ref"])
        ids = ids_of(body)
        prompt_text = reply_prompt(current, ids, str(body.get("extra") or ""))
        cfg = service.config()
        key = openai_api_key(service.folder, cfg["account"])
        model = str(cfg.get("openai_model") or MODEL_DEFAULT)
        answer, usage = complete(key, model, prompt_text)  # raises OpenAIError, shown to the owner like any other
        # Tokens only: never the prompt or the answer, same rule as every other log entry.
        service.log("openai_usage", model=model, **usage, reference=current["property_ref"],
                    cost_usd=round(estimate_cost_usd(model, **{
                        k: usage[k] for k in ("prompt_tokens", "completion_tokens")}), 6))
        return {**save_drafts_from(current, answer), "tokens": usage, "fuel": service.api_fuel(current["property_ref"])}

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

    def visit_candidates(body):
        return service.visit_candidates(body.get("property_ref") or None)

    def visit_analysis_prompt(body):
        return {"prompt": service.visit_analysis_prompt(body.get("property_ref") or None)}

    def visit_round_summary(body):
        return service.visit_round_summary(body.get("property_ref") or None)

    def visit_analyze(body):
        return service.analyze_visits(body.get("property_ref") or None)

    def visit_propose(body):
        emails = body.get("emails")
        if not isinstance(emails, list) or not all(isinstance(email, str) for email in emails):
            raise ValueError("Escolhe os clientes.")
        result = service.propose_visits(body.get("property_ref") or None, body.get("day"), body.get("start"),
                                        body.get("end"), emails)
        return {**result, "state": state(), "settings": service.settings()}

    def visits_close(body):
        result = service.close_visits(body.get("property_ref") or None)
        return {**result, "state": state(), "settings": service.settings()}

    def consent_request(body):
        result = service.request_consent(body.get("property_ref") or None)
        return {**result, "state": state()}

    def consent_confirm(body):
        message_id = str(body.get("id") or "")
        if not message_id:
            raise ValueError("Indica o email.")
        result = service.confirm_consent(message_id, body.get("property_ref") or None)
        return {**result, "state": state()}

    def property_prompts(body):
        service.save_prompts(str(body.get("reference") or ""), body.get("prompts") or {})
        return service.settings()

    def contact_save(body):
        return {**service.save_contact(body.get("contact") or {}), **service.contacts()}

    def contact_delete(body):
        result = service.delete_contact(body.get("email"), body.get("imovel") or None)
        return {**result, **service.contacts(), "state": state()}

    def contact_ignore(body):
        result = service.set_ignored(body.get("property_ref") or None, body.get("email"),
                                     bool(body.get("ignored", True)), str(body.get("reason") or ""),
                                     body.get("kind") or None)
        return {**result, "state": state()}

    def fuel_fill(body):
        return {"fuel": service.fill_fuel(body.get("property_ref") or None, body.get("capacity_eur"))}

    def property_panel(body):
        return {"panel": service.save_panel(body.get("property_ref") or None, body.get("reply_hours_max"),
                                            body.get("distance_km"), body.get("l_per_100km"))}

    def contacts_ignored(body):
        return service.ignored_contacts(body.get("property_ref") or None)

    def digest_save(body):
        return service.save_digest_text(body.get("text"))

    def digest_send(body):
        if body.get("confirmed") is not True:
            raise ValueError("Confirma o envio na página.")
        return service.send_digest(True)

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
        for name, value in (("TOKEN", token), ("NONCE", nonce), ("VERSION", DISPLAY_VERSION), ("BUILD_AT", build_at)):
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

    async def photo(request):
        # An <img> cannot send the token header, so the photo asks for the page's cookie instead.
        if not same(request.cookies.get(COOKIE), token):
            return PlainTextResponse("Abre o link mostrado no terminal ao iniciar a página.", 403)
        try:
            found = await run_in_threadpool(service.photo, request.path_params["ref"])
        except ValueError:
            found = None
        if not found:
            return PlainTextResponse("Sem fotografia.", 404)
        return Response(found[0], media_type=found[1], headers=HEADERS)

    async def contacts_csv(request):
        # A download link cannot send the token header either: the page's cookie is the proof, as for photos.
        if not same(request.cookies.get(COOKIE), token):
            return PlainTextResponse("Abre o link mostrado no terminal ao iniciar a página.", 403)
        try:
            data = await run_in_threadpool(one_at_a_time, lambda body: service.contacts_csv(), {})
        except (ValueError, RuntimeError) as exc:
            return PlainTextResponse(str(exc), 400)
        return Response(data, media_type="text/csv; charset=utf-8",
                        headers={**HEADERS, "Content-Disposition": 'attachment; filename="contactos.csv"'})

    def property_photo(body):
        service.save_photo(str(body.get("reference") or ""), body.get("image"))
        return service.settings()

    def knowledge_save(body):
        ref = body.get("property_ref") or None
        result = service.save_knowledge(ref, body.get("file"), body.get("text"), str(body.get("scope") or "property"))
        return {**result, "knowledge": service.knowledge(ref), "state": state()}

    def note(body):
        ref = body.get("property_ref") or None
        result = service.add_note(ref, body.get("text"), str(body.get("scope") or "property"))
        # The page shows the new knowledge at once, and the next prompt already carries it.
        return {**result, "knowledge": service.knowledge(ref), "state": state()}

    handlers = {"state": ("GET", lambda body: state()), "read": ("POST", read), "prompt": ("POST", prompt),
                "prompt/generate": ("POST", generate),
                "paste": ("POST", paste), "drafts": ("POST", drafts), "preview": ("POST", preview),
                "send": ("POST", send), "dismiss": ("POST", dismiss),
                "metrics": ("POST", lambda body: service.metrics(int(body.get("days") or 14))),
                "settings": ("GET", lambda body: service.settings()), "voice": ("POST", voice),
                "property/prompt": ("POST", property_prompt),
                "property/parse": ("POST", lambda body: {"fields": parse_listing(str(body.get("text") or ""))}),
                "property/save": ("POST", property_save), "property/prompts": ("POST", property_prompts),
                "property/photo": ("POST", property_photo), "property/panel": ("POST", property_panel),
                "visits/candidates": ("POST", visit_candidates), "visits/propose": ("POST", visit_propose),
                "visits/analysis-prompt": ("POST", visit_analysis_prompt), "visits/analyze": ("POST", visit_analyze),
                "visits/round-summary": ("POST", visit_round_summary), "visits/close": ("POST", visits_close),
                "consent/request": ("POST", consent_request), "consent/confirm": ("POST", consent_confirm),
                "contacts": ("GET", lambda body: service.contacts()),
                "contacts/save": ("POST", contact_save), "contacts/delete": ("POST", contact_delete),
                "contacts/ignore": ("POST", contact_ignore), "contacts/ignored": ("POST", contacts_ignored),
                "fuel/fill": ("POST", fuel_fill),
                "digest": ("GET", lambda body: service.digest_view()),
                "digest/save": ("POST", digest_save), "digest/send": ("POST", digest_send),
                "knowledge": ("POST", lambda body: service.knowledge(body.get("property_ref") or None)),
                "knowledge/note": ("POST", note), "knowledge/save": ("POST", knowledge_save)}
    routes = ([Route("/", page), Route("/photo/{ref}", photo), Route("/contactos.csv", contacts_csv)]
              + [Route(f"/{name}", asset(name)) for name in ASSETS]
              + [Route(f"/api/{name}", api(handler), methods=[method]) for name, (method, handler) in handlers.items()])
    app = Starlette(routes=routes)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    return app


def ours(pid):
    """Whether a process is this page (and not something else that happens to be running)."""
    command = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout
    return "main.py" in command or ("backend.cli" in command or "bot-mail" in command) and " web" in command


def stop_previous(folder):
    """A page left running for this folder is stopped first, so starting it again always just works."""
    try:
        pid = int((Path(folder) / ".page.pid").read_text().strip())
    except (OSError, ValueError):
        return
    if pid == os.getpid() or not ours(pid):
        return  # gone already, or the number now belongs to another program: never touch it
    os.kill(pid, signal.SIGTERM)
    for _ in range(40):  # up to 10 s for the old page to close
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.25)


def serve(folder, port=8765, open_browser=True):
    """Starts the page on 127.0.0.1 with a new token and opens the browser at the one link that works."""
    import uvicorn
    import webbrowser
    stop_previous(folder)
    (Path(folder) / ".page.pid").write_text(str(os.getpid()))
    token = secrets.token_urlsafe(24)
    url = f"http://127.0.0.1:{port}/?t={token}"
    print(f"Real Estate AI Assistant v{DISPLAY_VERSION}: {url}\nO link muda a cada arranque. Ctrl+C para parar.", flush=True)
    if open_browser:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    uvicorn.run(web_app(folder, token), host="127.0.0.1", port=port, access_log=False, log_level="warning")
