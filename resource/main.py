import os
import psycopg2, pulp
from fastapi import FastAPI, HTTPException
from routing import safest_route, ZONE_NODE

DB_URL = os.getenv("DATABASE_URL")
app = FastAPI(title="Resource Service")
NODE = ZONE_NODE

def q(sql):
    conn = psycopg2.connect(DB_URL); cur = conn.cursor(); cur.execute(sql)
    rows = cur.fetchall(); conn.close(); return rows

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/dispatch")
def dispatch():
    """Priority(z) = SI * Exposure / TravelTime, then LP assigns each team to at most one zone."""
    zones = q("""SELECT z.id, z.name, z.population, z.travel_time_min, COALESCE(d.severity_index,0)
                 FROM zones z LEFT JOIN LATERAL (SELECT severity_index FROM damage_scores
                 WHERE zone_id=z.id ORDER BY created_at DESC LIMIT 1) d ON TRUE""")
    teams = q("SELECT id, name, kind FROM resources WHERE available")
    max_pop = max(z[2] for z in zones)
    priority = {z[0]: z[4] * (z[2] / max_pop) / z[3] for z in zones}

    prob = pulp.LpProblem("dispatch", pulp.LpMaximize)
    x = {(t[0], z[0]): pulp.LpVariable(f"x_{t[0]}_{z[0]}", cat="Binary") for t in teams for z in zones}
    prob += pulp.lpSum(priority[z] * x[(t, z)] for (t, z) in x)
    for t in teams:                                    # each team -> at most one zone
        prob += pulp.lpSum(x[(t[0], z[0])] for z in zones) <= 1
    for z in zones:                                    # cap per zone so help spreads out
        prob += pulp.lpSum(x[(t[0], z[0])] for t in teams) <= 3
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    plan = []
    for (t, z), var in x.items():
        if var.value() == 1:
            team = next(tm for tm in teams if tm[0] == t)
            zone = next(zn for zn in zones if zn[0] == z)
            plan.append({"team": team[1], "kind": team[2], "zone_id": z, "zone": zone[1],
                         "priority": round(priority[z], 3),
                         "route": safest_route("Base", NODE[z])})
    plan.sort(key=lambda p: -p["priority"])
    return {"zones": [{"id": z[0], "name": z[1], "severity_index": z[4],
                       "priority": round(priority[z[0]], 3)} for z in zones], "plan": plan}

@app.get("/route")
def route(src: str, dst: str, closed: str = ""):
    closed_edges = [tuple(c.split("-")) for c in closed.split(",") if c]
    try:
        return safest_route(src, dst, closed_edges)
    except Exception:
        raise HTTPException(404, "no safe route")
