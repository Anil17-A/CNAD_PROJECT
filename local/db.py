"""SQLite stand-in for PostgreSQL+PostGIS (same tables, zone polygons stored as bounding boxes)."""
import sqlite3, threading, os

PATH = os.getenv("LOCAL_DB", ":memory:")
_lock = threading.RLock()
conn = sqlite3.connect(PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row

SCHEMA = """
CREATE TABLE IF NOT EXISTS zones (id INTEGER PRIMARY KEY, name TEXT, population INT, travel_time_min REAL,
  min_lon REAL, min_lat REAL, max_lon REAL, max_lat REAL);
CREATE TABLE IF NOT EXISTS sensor_readings (id INTEGER PRIMARY KEY AUTOINCREMENT, sensor_id TEXT, zone_id INT,
  type TEXT, value REAL, ts TEXT);
CREATE TABLE IF NOT EXISTS damage_scores (id INTEGER PRIMARY KEY AUTOINCREMENT, zone_id INT,
  structural_damage_pct REAL, population_exposure REAL, access_difficulty REAL, severity_index REAL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY, name TEXT, kind TEXT, units INT DEFAULT 1,
  available INT DEFAULT 1);
CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, zone_id INT, level TEXT, message TEXT,
  source TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

def init():
    with _lock:
        conn.executescript(SCHEMA)
        if not conn.execute("SELECT 1 FROM zones").fetchone():
            conn.executemany("INSERT INTO zones(name,population,travel_time_min,min_lon,min_lat,max_lon,max_lat) "
                             "VALUES (?,?,?,?,?,?,?)", [
                ("Riverside District 4", 52000, 18, 78.43, 17.50, 78.46, 17.53),
                ("Old Town",             38000, 25, 78.46, 17.50, 78.49, 17.53),
                ("Hillcrest",            15000, 40, 78.43, 17.53, 78.46, 17.56),
                ("Industrial Belt",      22000, 30, 78.46, 17.53, 78.49, 17.56),
                ("Lakeside",             31000, 22, 78.49, 17.50, 78.52, 17.53),
                ("Airport Road",         18000, 35, 78.52, 17.50, 78.55, 17.53),
                ("Tech Park",            45000, 28, 78.49, 17.53, 78.52, 17.56),
                ("Market Quarter",       41000, 20, 78.52, 17.53, 78.55, 17.56)])
            conn.executemany("INSERT INTO resources(name,kind,units) VALUES (?,?,1)", [
                ("Medical Team A", "medical"), ("Medical Team B", "medical"),
                ("Food Truck 1", "food"), ("Food Truck 2", "food"),
                ("Shelter Kit 1", "shelter"), ("Shelter Kit 2", "shelter"),
                ("Medical Team C", "medical"), ("Food Truck 3", "food"), ("Shelter Kit 3", "shelter")])
            conn.commit()

def execute(sql, params=()):
    with _lock:
        cur = conn.execute(sql, params); conn.commit(); return cur

def query(sql, params=()):
    with _lock:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
