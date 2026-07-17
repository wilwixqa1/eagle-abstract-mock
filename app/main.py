import base64
import json
import os
import random
import string
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Header, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"
# Set ORDERS_DIR to a Railway volume mount (e.g. /data) for persistence across deploys.
# Falls back to a local (ephemeral) directory when no volume is attached.
ORDERS = Path(os.environ.get("ORDERS_DIR", str(BASE / "orders")))
ORDERS.mkdir(parents=True, exist_ok=True)

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




# ---------- AI document extraction ----------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
EXTRACT_MODEL = os.environ.get("EXTRACT_MODEL", "claude-sonnet-4-6")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

EXTRACT_PROMPT = """You are helping a New York real-estate attorney pre-fill a title order form at a title insurance agency. Read the attached document (it may be a contract of sale, a prior title report, a deed, or a closing statement) and extract whatever order details it contains.

Respond with ONLY a JSON object - no preamble, no markdown fences. Use exactly these keys, and omit any key you cannot determine from the document. Never guess or invent values.

{
  "search_type": one of "Purchase" | "Refinance" | "Attorney Search" | "CO-OP Search",
  "purchase_price": e.g. "$750,000",
  "mortgage_amount": e.g. "$600,000",
  "closing_date": "YYYY-MM-DD",
  "property_type": one of "Residential" | "Commercial" | "Other",
  "coop_name": string,
  "address": full property street address,
  "county": NY county name,
  "city": city or town,
  "district": string, "section": string, "block": string, "lot": string,
  "sellers": seller/record owner name(s),
  "purchasers": purchaser name(s),
  "seller_firm": seller's attorney firm, "seller_name": seller's attorney name,
  "seller_email": string, "seller_phone": string,
  "lender_firm": lender name, "lender_name": lender contact,
  "lender_email": string, "lender_phone": string,
  "notes": one short sentence flagging anything ambiguous or worth the attorney's attention, if applicable
}

The district/section/block/lot may appear as "District/Section/Block/Lot", "SBL", or in a legal description. A cooperative apartment means search_type "CO-OP Search". If the document is clearly a purchase contract, search_type is "Purchase"."""

ALLOWED_UPLOAD_TYPES = {
    "application/pdf": "document",
    "image/png": "image",
    "image/jpeg": "image",
    "image/webp": "image",
}


@app.get("/api/extract/status")
def extract_status():
    return JSONResponse({"enabled": bool(ANTHROPIC_API_KEY)})


@app.post("/api/extract")
async def extract(req: Request, file: UploadFile = File(...)):
    if not ANTHROPIC_API_KEY:
        return JSONResponse(
            {"ok": False, "error": "Document extraction isn't configured on this deployment."},
            status_code=503,
        )
    if _rate_limited(req.client.host if req.client else "?", limit=10, window=600):
        return JSONResponse({"ok": False, "error": "Too many uploads. Please try again shortly."}, status_code=429)

    media_type = (file.content_type or "").lower()
    if media_type not in ALLOWED_UPLOAD_TYPES:
        return JSONResponse(
            {"ok": False, "error": "Please upload a PDF or an image (PNG/JPG). Word documents: save as PDF first."},
            status_code=415,
        )
    blob = await file.read()
    if len(blob) > MAX_UPLOAD_BYTES:
        return JSONResponse({"ok": False, "error": "File is over 10 MB. Please upload a smaller file."}, status_code=413)
    if not blob:
        return JSONResponse({"ok": False, "error": "The uploaded file was empty."}, status_code=400)

    block_type = ALLOWED_UPLOAD_TYPES[media_type]
    content_block = {
        "type": block_type,
        "source": {"type": "base64", "media_type": media_type, "data": base64.standard_b64encode(blob).decode()},
    }
    payload = {
        "model": EXTRACT_MODEL,
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": [content_block, {"type": "text", "text": EXTRACT_PROMPT}]}],
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
        body = r.json()
        if r.status_code != 200:
            msg = body.get("error", {}).get("message", "extraction service error")
            return JSONResponse({"ok": False, "error": f"Extraction failed: {msg}"}, status_code=502)
        text = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
        fields = _parse_extracted_json(text)
        if fields is None:
            return JSONResponse({"ok": False, "error": "Couldn't read structured details from that document."}, status_code=422)
        return JSONResponse({"ok": True, "fields": fields})
    except httpx.TimeoutException:
        return JSONResponse({"ok": False, "error": "Extraction timed out. Please try again."}, status_code=504)
    except Exception:
        return JSONResponse({"ok": False, "error": "Extraction failed unexpectedly."}, status_code=500)


ALLOWED_FIELDS = {
    "search_type", "purchase_price", "mortgage_amount", "closing_date", "property_type",
    "coop_name", "address", "county", "city", "district", "section", "block", "lot",
    "sellers", "purchasers", "seller_firm", "seller_name", "seller_email", "seller_phone",
    "lender_firm", "lender_name", "lender_email", "lender_phone", "notes",
}


def _parse_extracted_json(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        raw = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    return {k: str(v).strip() for k, v in raw.items() if k in ALLOWED_FIELDS and v and str(v).strip()}


@app.get("/admin")
def admin():
    return FileResponse(STATIC / "admin.html")


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
