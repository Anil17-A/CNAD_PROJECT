CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE zones (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  population INT NOT NULL,
  travel_time_min REAL NOT NULL,        -- base -> zone
  geom GEOMETRY(Polygon, 4326)
);

CREATE TABLE sensor_readings (
  id BIGSERIAL PRIMARY KEY,
  sensor_id TEXT, zone_id INT REFERENCES zones(id),
  type TEXT, value DOUBLE PRECISION, ts TIMESTAMPTZ
);
CREATE INDEX ON sensor_readings (zone_id, ts DESC);

CREATE TABLE damage_scores (
  id SERIAL PRIMARY KEY,
  zone_id INT REFERENCES zones(id),
  structural_damage_pct REAL, population_exposure REAL, access_difficulty REAL,
  severity_index REAL, created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE resources (
  id SERIAL PRIMARY KEY,
  name TEXT, kind TEXT CHECK (kind IN ('medical','food','shelter')),
  units INT DEFAULT 1, available BOOLEAN DEFAULT TRUE
);

CREATE TABLE alerts (
  id SERIAL PRIMARY KEY,
  zone_id INT, level TEXT, message TEXT, source TEXT, created_at TIMESTAMPTZ DEFAULT now()
);

-- Demo zones around Hyderabad (rectangles)
INSERT INTO zones (name, population, travel_time_min, geom) VALUES
 ('Riverside District 4', 52000, 18, ST_MakeEnvelope(78.43,17.50,78.46,17.53,4326)),
 ('Old Town',             38000, 25, ST_MakeEnvelope(78.46,17.50,78.49,17.53,4326)),
 ('Hillcrest',            15000, 40, ST_MakeEnvelope(78.43,17.53,78.46,17.56,4326)),
 ('Industrial Belt',      22000, 30, ST_MakeEnvelope(78.46,17.53,78.49,17.56,4326)),
 ('Lakeside',             31000, 22, ST_MakeEnvelope(78.49,17.50,78.52,17.53,4326)),
 ('Airport Road',         18000, 35, ST_MakeEnvelope(78.52,17.50,78.55,17.53,4326)),
 ('Tech Park',            45000, 28, ST_MakeEnvelope(78.49,17.53,78.52,17.56,4326)),
 ('Market Quarter',       41000, 20, ST_MakeEnvelope(78.52,17.53,78.55,17.56,4326));

INSERT INTO resources (name, kind, units) VALUES
 ('Medical Team A','medical',1),('Medical Team B','medical',1),
 ('Food Truck 1','food',1),('Food Truck 2','food',1),
 ('Shelter Kit 1','shelter',1),('Shelter Kit 2','shelter',1),
 ('Medical Team C','medical',1),('Food Truck 3','food',1),('Shelter Kit 3','shelter',1);
