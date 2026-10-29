import os, json
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel, Field
from kafka import KafkaProducer
from severity import compute_si, priority_label

BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
DB_URL = os.getenv("DATABASE_URL")
app = FastAPI(title="Damage Assessment Service")
_producer = None

def producer():
    global _producer
    if _producer is None:
        _producer = KafkaProducer(bootstrap_servers=BROKER, value_serializer=lambda v: json.dumps(v).encode())
    return _producer

class Assessment(BaseModel):
    zone_id: int
    structural_damage_pct: float = Field(ge=0, le=100)
    population_exposure: float = Field(ge=0, le=1)
    access_difficulty: float = Field(ge=0, le=1)

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/assess")
def assess(a: Assessment):
    si = compute_si(a.structural_damage_pct, a.population_exposure, a.access_difficulty)
    conn = psycopg2.connect(DB_URL); conn.autocommit = True; cur = conn.cursor()
    cur.execute("""INSERT INTO damage_scores(zone_id,structural_damage_pct,population_exposure,
                   access_difficulty,severity_index) VALUES (%s,%s,%s,%s,%s)""",
                (a.zone_id, a.structural_damage_pct, a.population_exposure, a.access_difficulty, si))
    conn.close()
    event = {"zone_id": a.zone_id, "severity_index": si, "priority": priority_label(si)}
    producer().send("damage.scores", event); producer().flush()
    return event

@app.get("/scores")
def scores():
    conn = psycopg2.connect(DB_URL); cur = conn.cursor()
    cur.execute("""SELECT DISTINCT ON (zone_id) zone_id, severity_index, created_at
                   FROM damage_scores ORDER BY zone_id, created_at DESC""")
    rows = [{"zone_id": r[0], "severity_index": r[1], "created_at": str(r[2])} for r in cur.fetchall()]
    conn.close(); return rows
