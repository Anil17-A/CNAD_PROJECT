"""Single-process version of the whole platform (no Docker/Kafka/Postgres needed).

Same services, same API paths as the Docker stack, behind the same API-key gateway:
  /api/ingestion/*  /api/prediction/*  /api/damage/*  /api/resource/*  /api/alert/*
Kafka -> in-memory bus (local/bus.py); PostgreSQL -> SQLite (local/db.py).
The business logic files (severity.py, model.py, routing.py) are the SAME ones the containers use.
"""
import os, sys, time, json, random, asyncio, threading, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("damage", "prediction", "resource"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import pulp
from fastapi import FastAPI, APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from severity import compute_si, priority_label
from model import risk_from_window
from routing import safest_route, ZONE_NODE
from local.bus import bus
from local import db

API_KEY = os.getenv("API_KEY", "change-me-demo-key")
RISK_T = float(os.getenv("RISK_ALERT_THRESHOLD", "0.6"))
SI_T = float(os.getenv("SEVERITY_ALERT_THRESHOLD", "60"))
SURGE_AFTER = float(os.getenv("SURGE_AFTER_SECONDS", "12"))
INTERVAL = float(os.getenv("SIM_INTERVAL_SECONDS", "1"))
DEDUP_SECONDS = float(os.getenv("ALERT_DEDUP_SECONDS", "30"))
NODE = ZONE_NODE
NUM_ZONES = int(os.getenv("NUM_ZONES", "8"))
VERBOSE_SENSORS = os.getenv("VERBOSE_SENSORS", "0") == "1"

C = {"g": "\033[32m", "y": "\033[33m", "r": "\033[31m", "c": "\033[36m", "d": "\033[2m", "0": "\033[0m"}
def log(tag, msg, colour="0"):
    print(f"{C['d']}{time.strftime('%H:%M:%S')}{C['0']} {C[colour]}[{tag:<10}]{C['0']} {msg}", flush=True)

# ---------------- shared state ----------------
windows = collections.defaultdict(lambda: collections.deque(maxlen=30))
latest_risk, alerts, last_risk_alert, ws_clients = {}, [], {}, set()
stats = {"stored": 0}
state = {"loop": None, "t0": time.time()}

# ---------------- ingestion (sensor.raw -> DB) ----------------
def ingest(m):
    db.execute("INSERT INTO sensor_readings(sensor_id,zone_id,type,value,ts) VALUES (?,?,?,?,?)",
               (m["sensor_id"], m["zone_id"], m["type"], m["value"], m["ts"]))
    stats["stored"] += 1
    if VERBOSE_SENSORS:
        log("ingestion", f"stored {m['sensor_id']} = {m['value']}", "d")

# ---------------- prediction (sensor.raw -> risk.events) ----------------
def predict(m):
    w = windows[m["zone_id"]]; w.append(m["value"])
    risk, minutes, ci = risk_from_window(list(w))
    ev = {"zone_id": m["zone_id"], "hazard": "flood", "risk": risk,
          "minutes_to_impact": minutes, "confidence_interval": ci, "ts": m["ts"]}
    latest_risk[m["zone_id"]] = ev
    if risk >= 0.3:
        if risk >= RISK_T:
            log("prediction", f"zone {ev['zone_id']} risk={risk:.2f} eta={minutes} min", "y")
        bus.publish("risk.events", ev)

# ---------------- alerts (risk.events / damage.scores -> alerts) ----------------
def publish_alert(a):
    a["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    alerts.insert(0, a); del alerts[100:]
    db.execute("INSERT INTO alerts(zone_id,level,message,source) VALUES (?,?,?,?)",
               (a["zone_id"], a["level"], a["message"], a["source"]))
    log("ALERT", f"{a['level']} zone {a['zone_id']}: {a['message']}", "r" if a["level"] == "CRITICAL" else "y")
    loop = state["loop"]
    if loop:
        asyncio.run_coroutine_threadsafe(_broadcast(a), loop)

async def _broadcast(a):
    for ws in list(ws_clients):
        try: await ws.send_json(a)
        except Exception: ws_clients.discard(ws)

def on_risk(m):
    if m["risk"] >= RISK_T:
        if time.time() - last_risk_alert.get(m["zone_id"], 0) < DEDUP_SECONDS:
            return                                              # de-duplicate
        last_risk_alert[m["zone_id"]] = time.time()
        publish_alert({"zone_id": m["zone_id"], "level": "WARNING", "source": "prediction",
                       "message": f"Flood risk {m['risk']:.0%}. Estimated impact in {m['minutes_to_impact']} min."})

def on_damage(m):
    if m["severity_index"] >= SI_T:
        publish_alert({"zone_id": m["zone_id"], "level": "CRITICAL", "source": "damage",
                       "message": f"Severity index {m['severity_index']} - first-wave dispatch recommended."})

bus.subscribe("sensor.raw", ingest)
bus.subscribe("sensor.raw", predict)
bus.subscribe("risk.events", on_risk)
bus.subscribe("damage.scores", on_damage)

# ---------------- simulator ----------------
def simulator(stop: threading.Event):
    start = time.time()
    log("simulator", f"started - zone 1 flood surge begins after {SURGE_AFTER:.0f}s", "c")
    surged = False
    while not stop.is_set():
        elapsed = time.time() - start
        for zone in range(1, NUM_ZONES + 1):
            v = 2.0 + random.gauss(0, 0.05)
            if zone == 1 and elapsed > SURGE_AFTER:
                v += 0.15 * (elapsed - SURGE_AFTER)
                if not surged:
                    surged = True; log("simulator", "!!! flood surge started in zone 1 (Riverside)", "c")
            bus.publish("sensor.raw", {"sensor_id": f"WL-{zone}", "zone_id": zone, "type": "water_level",
                                       "value": round(v, 3), "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        stop.wait(INTERVAL)

# ---------------- API ----------------
hits = collections.defaultdict(list)
def gateway(x_api_key: str = Header(default=None)):
    if x_api_key != API_KEY:
        raise HTTPException(401, "invalid API key")
    now = time.time(); hits["all"] = [t for t in hits["all"] if now - t < 60]
    if len(hits["all"]) >= 600:
        raise HTTPException(429, "rate limit exceeded")
    hits["all"].append(now)

app = FastAPI(title="Disaster Response Platform (local mode)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health(): return {"status": "ok", "uptime_s": round(time.time() - state["t0"], 1), "bus": dict(bus.counts)}

@app.get("/")
def dashboard(): return FileResponse(os.path.join(ROOT, "web", "index.html"))

ingestion = APIRouter(prefix="/api/ingestion", dependencies=[Depends(gateway)])
prediction = APIRouter(prefix="/api/prediction", dependencies=[Depends(gateway)])
damage = APIRouter(prefix="/api/damage", dependencies=[Depends(gateway)])
resource = APIRouter(prefix="/api/resource", dependencies=[Depends(gateway)])
alert = APIRouter(prefix="/api/alert", dependencies=[Depends(gateway)])

@ingestion.get("/health")
def i_health(): return {"status": "ok", "stored": stats["stored"]}

@ingestion.get("/readings/{zone_id}")
def readings(zone_id: int, limit: int = 50):
    return db.query("SELECT sensor_id,type,value,ts FROM sensor_readings WHERE zone_id=? ORDER BY id DESC LIMIT ?",
                    (zone_id, limit))

class Window(BaseModel):
    values: list[float]

@prediction.get("/health")
def p_health(): return {"status": "ok"}

@prediction.get("/risk")
def risk(): return latest_risk

@prediction.post("/predict")
def predict_endpoint(w: Window):
    r, m, ci = risk_from_window(w.values)
    return {"risk": r, "minutes_to_impact": m, "confidence_interval": ci}

class Assessment(BaseModel):
    zone_id: int
    structural_damage_pct: float = Field(ge=0, le=100)
    population_exposure: float = Field(ge=0, le=1)
    access_difficulty: float = Field(ge=0, le=1)

@damage.get("/health")
def d_health(): return {"status": "ok"}

@damage.post("/assess")
def assess(a: Assessment):
    si = compute_si(a.structural_damage_pct, a.population_exposure, a.access_difficulty)
    db.execute("INSERT INTO damage_scores(zone_id,structural_damage_pct,population_exposure,access_difficulty,"
               "severity_index) VALUES (?,?,?,?,?)",
               (a.zone_id, a.structural_damage_pct, a.population_exposure, a.access_difficulty, si))
    ev = {"zone_id": a.zone_id, "severity_index": si, "priority": priority_label(si)}
    log("damage", f"zone {a.zone_id} SI={si} -> {ev['priority']}", "g")
    bus.publish("damage.scores", ev)
    return ev

@damage.get("/scores")
def scores():
    return db.query("SELECT zone_id, severity_index, created_at FROM damage_scores WHERE id IN "
                    "(SELECT MAX(id) FROM damage_scores GROUP BY zone_id)")

@resource.get("/health")
def r_health(): return {"status": "ok"}

@resource.get("/dispatch")
def dispatch():
    """Priority(z) = SI * Exposure / TravelTime, then LP assigns each team to at most one zone."""
    zones = db.query("""SELECT z.id, z.name, z.population, z.travel_time_min,
                        COALESCE((SELECT severity_index FROM damage_scores WHERE zone_id=z.id
                                  ORDER BY id DESC LIMIT 1), 0) AS si FROM zones z""")
    teams = db.query("SELECT id, name, kind FROM resources WHERE available=1")
    max_pop = max(z["population"] for z in zones)
    prio = {z["id"]: z["si"] * (z["population"] / max_pop) / z["travel_time_min"] for z in zones}

    prob = pulp.LpProblem("dispatch", pulp.LpMaximize)
    x = {(t["id"], z["id"]): pulp.LpVariable(f"x_{t['id']}_{z['id']}", cat="Binary") for t in teams for z in zones}
    prob += pulp.lpSum(prio[z] * v for (t, z), v in x.items())
    for t in teams:
        prob += pulp.lpSum(x[(t["id"], z["id"])] for z in zones) <= 1
    for z in zones:
        prob += pulp.lpSum(x[(t["id"], z["id"])] for t in teams) <= 3
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    plan = []
    for (t, z), var in x.items():
        if var.value() and var.value() > 0.5:
            team = next(tm for tm in teams if tm["id"] == t); zone = next(zn for zn in zones if zn["id"] == z)
            plan.append({"team": team["name"], "kind": team["kind"], "zone_id": z, "zone": zone["name"],
                         "priority": round(prio[z], 3), "route": safest_route("Base", NODE[z])})
    plan.sort(key=lambda p: -p["priority"])
    return {"zones": [{"id": z["id"], "name": z["name"], "severity_index": z["si"],
                       "priority": round(prio[z["id"]], 3)} for z in zones], "plan": plan}

@resource.get("/route")
def route(src: str, dst: str, closed: str = ""):
    closed_edges = [tuple(c.split("-")) for c in closed.split(",") if c]
    try:
        return safest_route(src, dst, closed_edges)
    except Exception:
        raise HTTPException(404, "no safe route")

@alert.get("/health")
def a_health(): return {"status": "ok"}

@alert.get("/alerts")
def get_alerts(): return alerts

for r in (ingestion, prediction, damage, resource, alert):
    app.include_router(r)

@app.websocket("/api/alert/ws")
async def ws(websocket: WebSocket):
    await websocket.accept(); ws_clients.add(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        ws_clients.discard(websocket)

_stop = threading.Event()

@app.on_event("startup")
async def _startup():
    db.init()
    state["loop"] = asyncio.get_running_loop()
    if os.getenv("DISABLE_SIMULATOR") != "1":
        threading.Thread(target=simulator, args=(_stop,), daemon=True).start()

@app.on_event("shutdown")
def _shutdown(): _stop.set()
