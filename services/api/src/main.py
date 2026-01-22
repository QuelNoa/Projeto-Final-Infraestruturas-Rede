import asyncio
import json
import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="API", version="1.0")

AUTH_URL = os.getenv("AUTH_URL", "https://auth:8000/validate")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "secreto123")

# CA da tua PKI (cert-manager) montada em /etc/resilience-ca/ca.crt
AUTH_CA_FILE = os.getenv("AUTH_CA_FILE", "/etc/resilience-ca/ca.crt")


def log(event: str, **fields: Any) -> None:
    payload = {"ts": time.time(), "service": "api", "event": event, **fields}
    print(json.dumps(payload, ensure_ascii=False), flush=True)


@app.middleware("http")
async def access_log(request: Request, call_next):
    t0 = time.time()
    try:
        resp = await call_next(request)
        dt = (time.time() - t0) * 1000
        log("http", method=request.method, path=request.url.path, status=resp.status_code, lat_ms=int(dt))
        return resp
    except Exception as e:
        dt = (time.time() - t0) * 1000
        log("http_error", method=request.method, path=request.url.path, error=str(e), lat_ms=int(dt))
        raise


@app.get("/ping")
def ping():
    return {"msg": "pong", "service": "api"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/work")
async def work(n: int = 400000):
    """
    Endpoint CPU-bound para:
    - gerar carga real (HPA)
    - ser alvo de rate limiting no Ingress
    """
    log("work_start", n=n)

    def cpu_bound():
        s = 0
        for i in range(n):
            s += i * i
        return s

    loop = asyncio.get_event_loop()
    t0 = time.time()
    _ = await loop.run_in_executor(None, cpu_bound)
    dt = time.time() - t0

    log("work_done", n=n, compute_s=round(dt, 3))
    return {"result": "done", "compute_s": round(dt, 3)}


@app.get("/secure-data")
async def secure_data():
    """
    Demonstração de comunicação interna com TLS *verificado*:
    API -> AUTH via HTTPS, validando CA.
    """
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

    try:
        async with httpx.AsyncClient(verify=AUTH_CA_FILE, timeout=3.0) as client:
            r = await client.get(AUTH_URL, headers=headers)
    except Exception as e:
        log("auth_call_failed", error=str(e))
        raise HTTPException(status_code=503, detail="auth_unreachable")

    log("auth_call", status=r.status_code)
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="unauthorized")

    return {"secret": "42", "auth": "valid"}
