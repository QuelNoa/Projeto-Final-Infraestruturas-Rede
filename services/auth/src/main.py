import json
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="Auth", version="1.0")

TOKEN = "secreto123"


def log(event: str, **fields: Any) -> None:
    payload = {"ts": time.time(), "service": "auth", "event": event, **fields}
    print(json.dumps(payload, ensure_ascii=False), flush=True)


@app.middleware("http")
async def access_log(request: Request, call_next):
    t0 = time.time()
    resp = await call_next(request)
    dt = (time.time() - t0) * 1000
    log("http", method=request.method, path=request.url.path, status=resp.status_code, lat_ms=int(dt))
    return resp


@app.get("/validate")
def validate(authorization: str = Header(None)):
    if authorization == f"Bearer {TOKEN}":
        return {"status": "valid"}
    raise HTTPException(status_code=401, detail="invalid_token")


@app.get("/health")
def health():
    return {"status": "ok"}

