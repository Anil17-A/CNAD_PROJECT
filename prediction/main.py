import os, json, time, threading, collections
from fastapi import FastAPI
from pydantic import BaseModel
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
from model import risk_from_window

BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
app = FastAPI(title="Prediction Service")
windows = collections.defaultdict(lambda: collections.deque(maxlen=30))
latest = {}

def worker():
    while True:
        try:
            consumer = KafkaConsumer("sensor.raw", bootstrap_servers=BROKER, group_id="prediction",
                                     value_deserializer=lambda b: json.loads(b.decode()),
                                     auto_offset_reset="latest")
            producer = KafkaProducer(bootstrap_servers=BROKER,
                                     value_serializer=lambda v: json.dumps(v).encode())
            break
        except NoBrokersAvailable:
            print("waiting for kafka..."); time.sleep(3)
    for msg in consumer:
        m = msg.value
        w = windows[m["zone_id"]]; w.append(m["value"])
        risk, minutes, ci = risk_from_window(list(w))
        event = {"zone_id": m["zone_id"], "hazard": "flood", "risk": risk,
                 "minutes_to_impact": minutes, "confidence_interval": ci, "ts": m["ts"]}
        latest[m["zone_id"]] = event
        if risk >= 0.3:
            producer.send("risk.events", event)

@app.on_event("startup")
def start():
    threading.Thread(target=worker, daemon=True).start()

class Window(BaseModel):
    values: list[float]

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/risk")
def risk(): return latest

@app.post("/predict")
def predict(w: Window):
    r, m, ci = risk_from_window(w.values)
    return {"risk": r, "minutes_to_impact": m, "confidence_interval": ci}
