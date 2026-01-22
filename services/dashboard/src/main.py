import json
import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="Dashboard", version="1.0")

API_PUBLIC = os.getenv("API_PUBLIC", "https://api.resilience.local")


def log(event: str, **fields: Any) -> None:
    payload = {"ts": time.time(), "service": "dashboard", "event": event, **fields}
    print(json.dumps(payload, ensure_ascii=False), flush=True)


@app.middleware("http")
async def access_log(request: Request, call_next):
    t0 = time.time()
    resp = await call_next(request)
    dt = (time.time() - t0) * 1000
    log("http", method=request.method, path=request.url.path, status=resp.status_code, lat_ms=int(dt))
    return resp


HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Resilience Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    .card { padding: 16px; border: 1px solid #ddd; border-radius: 8px; width: 520px; }
    .ok { color: #0a0; }
    .bad { color: #a00; }
    code { background: #f5f5f5; padding: 2px 6px; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>Dashboard de Resiliência</h1>
  <div class="card">
    <p>API: <span id="api">...</span></p>
    <p>Auth (via API /secure-data): <span id="secure">...</span></p>
    <p>Endpoints monitorizados: <code>/ping</code>, <code>/secure-data</code></p>
  </div>

<script>
async function upd() {
  try {
    let r1 = await fetch('https://api.resilience.local/ping', { cache: 'no-store' });
    document.getElementById('api').innerHTML = (r1.ok ? '<b class="ok">OK</b>' : '<b class="bad">FAIL</b>') + ' (' + r1.status + ')';
  } catch(e) {
    document.getElementById('api').innerHTML = '<b class="bad">DOWN</b>';
  }

  try {
    let r2 = await fetch('https://api.resilience.local/secure-data', { cache: 'no-store' });
    document.getElementById('secure').innerHTML = (r2.ok ? '<b class="ok">OK</b>' : '<b class="bad">FAIL</b>') + ' (' + r2.status + ')';
  } catch(e) {
    document.getElementById('secure').innerHTML = '<b class="bad">DOWN</b>';
  }
}
setInterval(upd, 3000);
upd();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


@app.get("/health")
def health():
    return {"status": "ok"}
