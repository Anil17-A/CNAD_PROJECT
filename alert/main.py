import os, json, time, asyncio, threading
import psycopg2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
DB_URL = os.getenv("DATABASE_URL")
RISK_T = float(os.getenv("RISK_ALERT_THRESHOLD", "0.6"))
SI_T = float(os.getenv("SEVERITY_ALERT_THRESHOLD", "60"))

app = FastAPI(title="Alert Service")
alerts, clients, last_risk_alert = [], set(), {}
loop = None

async def broadcast(a):
    for ws in list(clients):
        try: await ws.send_json(a)
        except Exception: clients.discard(ws)

def publish(a):
    alerts.insert(0, a); del alerts[100:]
    try:
        conn = psycopg2.connect(DB_URL); conn.autocommit = True
        conn.cursor().execute("INSERT INTO alerts(zone_id,level,message,source) VALUES (%s,%s,%s,%s)",
                              (a["zone_id"], a["level"], a["message"], a["source"])); conn.close()
    except Exception as e: print("db error", e)
    if loop: asyncio.run_coroutine_threadsafe(broadcast(a), loop)

def worker():
    while True:
        try:
            c = KafkaConsumer("risk.events", "damage.scores", bootstrap_servers=BROKER, group_id="alert",
                              value_deserializer=lambda b: json.loads(b.decode()), auto_offset_reset="latest")
            break
        except NoBrokersAvailable:
            print("waiting for kafka..."); time.sleep(3)
    for msg in c:
        m = msg.value
        if msg.topic == "risk.events" and m["risk"] >= RISK_T:
            if time.time() - last_risk_alert.get(m["zone_id"], 0) < 30: continue   # de-duplicate
            last_risk_alert[m["zone_id"]] = time.time()
            publish({"zone_id": m["zone_id"], "level": "WARNING", "source": "prediction",
                     "message": f"Flood risk {m['risk']:.0%}. Estimated impact in {m['minutes_to_impact']} min."})
        elif msg.topic == "damage.scores" and m["severity_index"] >= SI_T:
            publish({"zone_id": m["zone_id"], "level": "CRITICAL", "source": "damage",
                     "message": f"Severity index {m['severity_index']} - first-wave dispatch recommended."})

@app.on_event("startup")
async def start():
    global loop; loop = asyncio.get_running_loop()
    threading.Thread(target=worker, daemon=True).start()

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/alerts")
def get_alerts(): return alerts

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept(); clients.add(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)
