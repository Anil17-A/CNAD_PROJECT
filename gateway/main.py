import os, time, collections
import httpx
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

API_KEY = os.getenv("API_KEY", "change-me-demo-key")
SERVICES = {"ingestion", "prediction", "damage", "resource", "alert"}
RATE_LIMIT = 120  # requests / minute / client

app = FastAPI(title="API Gateway")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
hits = collections.defaultdict(list)

@app.get("/health")
def health(): return {"status": "ok"}

@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(service: str, path: str, request: Request):
    if request.headers.get("x-api-key") != API_KEY:
        raise HTTPException(401, "invalid API key")
    if service not in SERVICES:
        raise HTTPException(404, "unknown service")
    now, ip = time.time(), request.client.host
    hits[ip] = [t for t in hits[ip] if now - t < 60]
    if len(hits[ip]) >= RATE_LIMIT:
        raise HTTPException(429, "rate limit exceeded")
    hits[ip].append(now)
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.request(request.method, f"http://{service}:8000/{path}",
                                 params=request.query_params, content=await request.body(),
                                 headers={"content-type": request.headers.get("content-type", "application/json")})
    return Response(r.content, r.status_code, media_type=r.headers.get("content-type"))
