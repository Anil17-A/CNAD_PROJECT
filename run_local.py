#!/usr/bin/env python3
"""Run the whole platform locally - no Docker needed.

    python run_local.py              # start platform + dashboard, run scripted demo, keep serving
    python run_local.py --demo-only  # run the demo and exit
    python run_local.py --no-demo    # just serve (dashboard http://localhost:8000)
"""
import argparse, json, sys, threading, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import httpx, uvicorn
from local.app import app, API_KEY, SURGE_AFTER, log

BASE = "http://127.0.0.1:8000"
H = {"x-api-key": API_KEY}

def banner(port):
    url = f"http://localhost:{port}"
    print("\n\033[1;32m" + "=" * 58)
    print(f"  Dashboard : {url}")
    print(f"  API docs  : {url}/docs")
    print("  (Ctrl+Click the link to open it, Ctrl+C to stop)")
    print("=" * 58 + "\033[0m\n", flush=True)

def show(title, data):
    print(f"\n\033[1m=== {title} ===\033[0m")
    print(json.dumps(data, indent=2) if not isinstance(data, str) else data, flush=True)

def demo(c: httpx.Client):
    show("1) Gateway security check", f"no key -> HTTP {c.get('/api/alert/alerts').status_code} (expected 401); "
                                       f"with key -> HTTP {c.get('/api/alert/alerts', headers=H).status_code}")
    show("2) Service health", {s: c.get(f"/api/{s}/health", headers=H).json()
                               for s in ("ingestion", "prediction", "damage", "resource", "alert")})
    show("3) Direct prediction call (calm vs surge window)", {
        "calm": c.post("/api/prediction/predict", headers=H, json={"values": [2.0, 2.01, 1.99] * 5}).json(),
        "surge": c.post("/api/prediction/predict", headers=H,
                        json={"values": [2.0] * 20 + [2.5, 3.0, 3.6, 4.3, 5.0]}).json()})
    wait = SURGE_AFTER + 8
    print(f"\nwaiting {wait:.0f}s for the simulated flood surge in zone 1 ...", flush=True)
    time.sleep(wait)
    show("4) Alerts raised by the early-warning pipeline", c.get("/api/alert/alerts", headers=H).json())
    show("5) Latest risk per zone", c.get("/api/prediction/risk", headers=H).json())
    show("6) Damage assessment - Riverside (deck worked example, expect SI 62.3 HIGH)",
         c.post("/api/damage/assess", headers=H, json={"zone_id": 1, "structural_damage_pct": 62,
                "population_exposure": 0.81, "access_difficulty": 0.35}).json())
    for z, dmg, exp, acc in [(2, 30, 0.5, 0.2), (5, 45, 0.6, 0.3), (7, 75, 0.9, 0.4), (8, 20, 0.7, 0.1)]:
        c.post("/api/damage/assess", headers=H, json={"zone_id": z, "structural_damage_pct": dmg,
               "population_exposure": exp, "access_difficulty": acc})
    d = c.get("/api/resource/dispatch", headers=H).json()
    show("7) Zone priorities", d["zones"])
    show("8) LP dispatch plan (team -> zone, Dijkstra route)",
         "\n".join(f"{p['team']:<15} -> {p['zone']:<22} prio={p['priority']:<6} "
                   f"{' > '.join(p['route']['path'])} ({p['route']['minutes']} min)" for p in d["plan"]))
    show("9) Rerouting with Base-Riverside road flooded",
         c.get("/api/resource/route", headers=H, params={"src": "Base", "dst": "Riverside",
                                                         "closed": "Base-Riverside"}).json())
    show("10) Stored sensor readings (latest 3, zone 1)", c.get("/api/ingestion/readings/1", headers=H,
                                                                  params={"limit": 3}).json())
    show("Platform stats", c.get("/health").json())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo-only", action="store_true"); ap.add_argument("--no-demo", action="store_true")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=a.port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    with httpx.Client(base_url=BASE.replace("8000", str(a.port)), timeout=30) as c:
        for _ in range(50):
            try: c.get("/health"); break
            except httpx.TransportError: time.sleep(0.2)
        log("platform", f"up - API key: {API_KEY}", "g")
        banner(a.port)
        if not a.no_demo:
            demo(c)
        if a.demo_only:
            server.should_exit = True; return
    banner(a.port)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        server.should_exit = True; print("\nstopped")

if __name__ == "__main__":
    main()
