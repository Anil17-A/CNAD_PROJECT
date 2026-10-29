import os, json, time, threading
import psycopg2
from fastapi import FastAPI
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
DB_URL = os.getenv("DATABASE_URL")
app = FastAPI(title="Ingestion Service")
stats = {"stored": 0}

def worker():
    while True:
        try:
            consumer = KafkaConsumer("sensor.raw", bootstrap_servers=BROKER, group_id="ingestion",
                                     value_deserializer=lambda b: json.loads(b.decode()),
                                     auto_offset_reset="latest")
            conn = psycopg2.connect(DB_URL); conn.autocommit = True
            break
        except (NoBrokersAvailable, psycopg2.OperationalError):
            print("waiting for kafka/db..."); time.sleep(3)
    cur = conn.cursor()
    for msg in consumer:
        m = msg.value
        cur.execute("INSERT INTO sensor_readings(sensor_id,zone_id,type,value,ts) VALUES (%s,%s,%s,%s,%s)",
                    (m["sensor_id"], m["zone_id"], m["type"], m["value"], m["ts"]))
        stats["stored"] += 1

@app.on_event("startup")
def start():
    threading.Thread(target=worker, daemon=True).start()

@app.get("/health")
def health(): return {"status": "ok", "stored": stats["stored"]}

@app.get("/readings/{zone_id}")
def readings(zone_id: int, limit: int = 50):
    conn = psycopg2.connect(DB_URL); cur = conn.cursor()
    cur.execute("SELECT sensor_id,type,value,ts FROM sensor_readings WHERE zone_id=%s ORDER BY ts DESC LIMIT %s",
                (zone_id, limit))
    rows = [{"sensor_id": r[0], "type": r[1], "value": r[2], "ts": str(r[3])} for r in cur.fetchall()]
    conn.close(); return rows
