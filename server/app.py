"""One small server for the GUI and the MCP (plan, "Server and hosting").

Routes: GET / (choose a requirement, then the inputs), POST /parse (pasted lines, shown
parsed), POST /check (the result page), POST /check.json (the result's JSON, the same bytes as
the MCP's check_diet), POST /edit (back to the inputs), GET /about (hosting, privacy and
contact, from pages/about.html), GET /static/style.css, and /mcp (MCP, stateless Streamable
HTTP).

Limits: request bodies of at most 32 KB; known fields only; Host checked on every request and
Origin on every POST; a content security policy with no scripts; no cross-origin access. The
server logs no request bodies (run uvicorn with --no-access-log; the About page says so) and
fetches no URLs.

Environment: OAN_DATA (the data folder, default ../data), OAN_HOSTS (allowed host names,
comma-separated, default localhost,127.0.0.1), OAN_ORIGINS (allowed origins, default
http://localhost:8790,http://127.0.0.1:8790).
"""

import contextlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager  # noqa: E402
from starlette.applications import Starlette  # noqa: E402
from starlette.middleware import Middleware  # noqa: E402
from starlette.middleware.trustedhost import TrustedHostMiddleware  # noqa: E402
from starlette.responses import HTMLResponse, PlainTextResponse, Response  # noqa: E402
from starlette.routing import Mount, Route  # noqa: E402
from starlette.staticfiles import StaticFiles  # noqa: E402

import gui  # noqa: E402
import mcp_tools  # noqa: E402
from oan import result  # noqa: E402

MAX_BODY = 32 * 1024
DATA = result.Data(os.environ.get("OAN_DATA", os.path.join(ROOT, "data")))
HOSTS = [h.strip() for h in os.environ.get("OAN_HOSTS", "localhost,127.0.0.1").split(",")]
ORIGINS = [o.strip() for o in os.environ.get(
    "OAN_ORIGINS", "http://localhost:8790,http://127.0.0.1:8790").split(",")]
HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'self'; form-action 'self'; "
                               "frame-ancestors 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
    # same-origin, not no-referrer: under no-referrer a browser sends "Origin: null" with a
    # form, which the Origin check must refuse (found in the steward's GUI review, 22 Oct).
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",
    "Strict-Transport-Security": "max-age=31536000",
}


class Limits:
    """Pure ASGI middleware: the body size cap, the Origin check on POST, the headers."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1")
                   for k, v in scope.get("headers", [])}
        length = headers.get("content-length")
        if length is not None and (not length.isdigit() or int(length) > MAX_BODY):
            return await PlainTextResponse("Request too large", 413)(scope, receive, send)
        origin = headers.get("origin")
        if scope["method"] not in ("GET", "HEAD") and origin is not None and \
                origin not in ORIGINS:
            return await PlainTextResponse("Origin not allowed", 403)(scope, receive, send)
        seen = 0

        async def limited():
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > MAX_BODY:
                    raise BodyTooLarge()
            return message

        async def with_headers(message):
            if message["type"] == "http.response.start":
                extra = [(k.lower().encode(), v.encode()) for k, v in HEADERS.items()]
                message = dict(message, headers=list(message.get("headers", [])) + extra)
            await send(message)

        try:
            await self.app(scope, limited, with_headers)
        except BodyTooLarge:
            await PlainTextResponse("Request too large", 413)(scope, receive, send)


class BodyTooLarge(Exception):
    pass


async def form_items(request):
    form = await request.form(max_files=0, max_fields=400)
    return [(k, v) for k, v in form.multi_items() if isinstance(v, str)]


def bad(text):
    return HTMLResponse(gui.page(DATA, "<p class=\"error\">%s</p>" % gui.e(text), "Error"), 400)


with open(os.path.join(HERE, "pages", "about.html"), encoding="utf-8") as f:
    ABOUT = f.read()


async def about(request):
    return HTMLResponse(gui.page(DATA, ABOUT, "About"))


async def home(request):
    rid = request.query_params.get("requirement")
    if rid and any(r["id"] == rid for r in DATA.tables["requirements"]):
        return HTMLResponse(gui.page(DATA, gui.step2(DATA, rid), "Enter values"))
    return HTMLResponse(gui.page(DATA, gui.step1(DATA), "Choose a requirement"))


async def parse(request):
    items = await form_items(request)
    try:
        req = gui.request_from_form(DATA, items)
    except gui.FormError as err:
        return bad(str(err))
    rid = req.get("requirement")
    if not any(r["id"] == rid for r in DATA.tables["requirements"]):
        return bad("Choose a requirement first.")
    paste = next((v for k, v in items if k == "paste"), "")
    entries, parsed, not_understood = gui.parse_paste(DATA, paste)
    req["entries"] = entries
    return HTMLResponse(gui.page(DATA, gui.step2(
        DATA, rid, req, gui.parsed_message(DATA, parsed, not_understood)), "Enter values"))


async def _checked(request):
    items = await form_items(request)
    req = gui.request_from_form(DATA, items)
    return req, result.check(DATA, req)


async def check(request):
    try:
        req, res = await _checked(request)
    except (gui.FormError, result.RequestError) as err:
        return bad(str(err))
    return HTMLResponse(gui.result_page(DATA, req, res))


async def check_json(request):
    try:
        _, res = await _checked(request)
    except (gui.FormError, result.RequestError) as err:
        return PlainTextResponse(str(err), 400)
    return Response(result.to_json(res).encode("utf-8"), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="oan-result.json"'})


async def edit(request):
    items = await form_items(request)
    try:
        req = gui.request_from_form(DATA, items)
    except gui.FormError as err:
        return bad(str(err))
    rid = req.get("requirement")
    if not any(r["id"] == rid for r in DATA.tables["requirements"]):
        return HTMLResponse(gui.page(DATA, gui.step1(DATA), "Choose a requirement"))
    return HTMLResponse(gui.page(DATA, gui.step2(DATA, rid, req), "Enter values"))


session_manager = StreamableHTTPSessionManager(app=mcp_tools.build(DATA), stateless=True,
                                               json_response=True,
                                               max_request_body_size=MAX_BODY)


class MCPEndpoint:
    """/mcp itself (no redirect to /mcp/): the SDK's stateless Streamable HTTP handler."""

    async def __call__(self, scope, receive, send):
        await session_manager.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(app):
    async with session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/", home, methods=["GET"]),
        Route("/parse", parse, methods=["POST"]),
        Route("/check", check, methods=["POST"]),
        Route("/check.json", check_json, methods=["POST"]),
        Route("/edit", edit, methods=["POST"]),
        Route("/about", about, methods=["GET"]),
        Mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static"),
        Route("/mcp", MCPEndpoint(), methods=["GET", "POST", "DELETE"]),
    ],
    middleware=[Middleware(TrustedHostMiddleware, allowed_hosts=HOSTS), Middleware(Limits)],
    lifespan=lifespan,
)
