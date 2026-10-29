"""End-to-end API test of the Docker-free local platform (no simulator, no network)."""
import os, sys
os.environ["DISABLE_SIMULATOR"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient
from local.app import app, API_KEY

H = {"x-api-key": API_KEY}

def test_api_flow():
    with TestClient(app) as c:
        assert c.get("/api/alert/alerts").status_code == 401
        r = c.post("/api/damage/assess", headers=H, json={"zone_id": 1, "structural_damage_pct": 62,
                   "population_exposure": 0.81, "access_difficulty": 0.35}).json()
        assert r["severity_index"] == 62.3 and r["priority"] == "HIGH"
        alerts = c.get("/api/alert/alerts", headers=H).json()
        assert alerts and alerts[0]["level"] == "CRITICAL"
        d = c.get("/api/resource/dispatch", headers=H).json()
        assert d["plan"] and d["plan"][0]["zone_id"] == 1
        rr = c.get("/api/resource/route", headers=H, params={"src": "Base", "dst": "Riverside", "closed": "Base-Riverside"}).json()
        assert rr["path"] == ["Base", "OldTown", "Riverside"]
