import json
import os
import random
import string
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"
ORDERS = BASE / "orders"          # mock persistence (ephemeral on Railway); prod = email relay
ORDERS.mkdir(exist_ok=True)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "eagle2026")
_last_hits = defaultdict(list)    # naive per-IP rate limit

app = FastAPI(title="Eagle Abstract mock")


def _rate_limited(ip: str, limit: int = 5, window: int = 300) -> bool:
    now = time.time()
    hits = [t for t in _last_hits[ip] if now - t < window]
    _last_hits[ip] = hits
    if len(hits) >= limit:
        return True
    _last_hits[ip].append(now)
    return False


def _spam_check(data: dict, ip: str):
    """Honeypot + timing trap + rate limit. Returns error response or None."""
    if data.get("website"):  # honeypot field, hidden from humans
        return JSONResponse({"ok": True, "ref": "EA-000000-0000"})  # silently discard
    try:
        elapsed = time.time() - float(data.get("_t", 0)) / 1000.0
    except (TypeError, ValueError):
        elapsed = 999
    if 0 < elapsed < 3:  # form completed in under 3 seconds = bot
        return JSONResponse({"ok": True, "ref": "EA-000000-0000"})
    if _rate_limited(ip):
        return JSONResponse(
            {"ok": False, "error": "Too many submissions. Please call 631-549-8848."},
            status_code=429,
        )
    return None


def _save(prefix: str, payload: dict) -> str:
    ref = "{}-{}-{}".format(
        prefix,
        datetime.now(timezone.utc).strftime("%y%m%d"),
        "".join(random.choices(string.digits, k=4)),
    )
    record = {"ref": ref, "received_at": datetime.now(timezone.utc).isoformat(), "data": payload}
    (ORDERS / f"{ref}.json").write_text(json.dumps(record, indent=2))
    return ref


@app.get("/healthz")
def healthz():
    return JSONResponse({"ok": True, "service": "eagle-abstract-mock"})


@app.post("/api/order")
async def submit_order(req: Request):
    try:
        data = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid payload"}, status_code=400)
    blocked = _spam_check(data, req.client.host if req.client else "?")
    if blocked is not None:
        return blocked
    data.pop("_t", None)
    data.pop("website", None)
    ref = _save("EA", data)
    # PROD TODO: email intake copy to Eagle + confirmation to client_email
    return JSONResponse({"ok": True, "ref": ref})


@app.post("/api/contact")
async def submit_contact(req: Request):
    try:
        data = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid payload"}, status_code=400)
    blocked = _spam_check(data, req.client.host if req.client else "?")
    if blocked is not None:
        return blocked
    data.pop("_t", None)
    data.pop("website", None)
    ref = _save("MSG", data)
    # PROD TODO: relay to customerservice@ inbox
    return JSONResponse({"ok": True, "ref": ref})


@app.get("/api/admin/submissions")
def admin_submissions(x_admin_password: str = Header(default="")):
    if x_admin_password != ADMIN_PASSWORD:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    subs = []
    for f in sorted(ORDERS.glob("*.json"), reverse=True):
        subs.append(json.loads(f.read_text()))
    return JSONResponse({"ok": True, "count": len(subs), "submissions": subs})


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/order")
def order():
    return FileResponse(STATIC / "order.html")


@app.get("/forms")
def forms():
    return FileResponse(STATIC / "forms.html")


@app.get("/about")
def about():
    return FileResponse(STATIC / "about.html")


@app.get("/fees")
def fees():
    return FileResponse(STATIC / "fees.html")


@app.get("/contact")
def contact():
    return FileResponse(STATIC / "contact.html")


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
