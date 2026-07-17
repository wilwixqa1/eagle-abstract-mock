import json
import random
import string
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"
ORDERS = BASE / "orders"          # mock persistence; swap for email relay in prod
ORDERS.mkdir(exist_ok=True)

app = FastAPI(title="Eagle Abstract mock")

@app.get("/healthz")
def healthz():
    return JSONResponse({"ok": True, "service": "eagle-abstract-mock"})

@app.post("/api/order")
async def submit_order(req: Request):
    try:
        data = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid payload"}, status_code=400)
    ref = "EA-{}-{}".format(
        datetime.now(timezone.utc).strftime("%y%m%d"),
        "".join(random.choices(string.digits, k=4)),
    )
    record = {"ref": ref, "received_at": datetime.now(timezone.utc).isoformat(), "order": data}
    (ORDERS / f"{ref}.json").write_text(json.dumps(record, indent=2))
    # PROD TODO: email intake copy to Eagle + confirmation to client_email
    return JSONResponse({"ok": True, "ref": ref})

@app.post("/api/contact")
async def submit_contact(req: Request):
    try:
        data = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid payload"}, status_code=400)
    ref = "MSG-{}-{}".format(
        datetime.now(timezone.utc).strftime("%y%m%d"),
        "".join(random.choices(string.digits, k=4)),
    )
    (ORDERS / f"{ref}.json").write_text(json.dumps({"ref": ref, "message": data}, indent=2))
    # PROD TODO: relay to customerservice@ inbox
    return JSONResponse({"ok": True, "ref": ref})

@app.get("/contact")
def contact():
    return FileResponse(STATIC / "contact.html")

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

app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
