"""Publishes fake sensor readings to Kafka. Zone 1 starts surging after SURGE_AFTER_SECONDS."""
import os, json, time, random
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
SURGE_AFTER = int(os.getenv("SURGE_AFTER_SECONDS", "30"))
INTERVAL = float(os.getenv("SIM_INTERVAL_SECONDS", "1"))

def connect():
    while True:
        try:
            return KafkaProducer(bootstrap_servers=BROKER,
                                 value_serializer=lambda v: json.dumps(v).encode())
        except NoBrokersAvailable:
            print("waiting for kafka..."); time.sleep(3)

p = connect()
start = time.time()
print("simulator started")
while True:
    elapsed = time.time() - start
    for zone in range(1, int(os.getenv("NUM_ZONES", "8")) + 1):
        value = 2.0 + random.gauss(0, 0.05)              # normal water level (m)
        if zone == 1 and elapsed > SURGE_AFTER:
            value += 0.15 * (elapsed - SURGE_AFTER)      # flood surge
        p.send("sensor.raw", {"sensor_id": f"WL-{zone}", "zone_id": zone,
                              "type": "water_level", "value": round(value, 3),
                              "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    p.flush()
    time.sleep(INTERVAL)
