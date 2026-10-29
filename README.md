# AI-Assisted Disaster Response & Emergency Coordination Platform (CNAD Review-2)

Microservices: **Ingestion, Prediction, Damage Assessment, Resource, Alert** behind an **API Gateway**,
with Redpanda (Kafka API), PostgreSQL+PostGIS, a Leaflet dashboard, and Kubernetes manifests.

## Folder structure
```
cnad-disaster-platform/
├── docker-compose.yml        # whole stack for local run
├── .env.example              # copy to .env
├── Makefile                  # up / demo / test / k8s-*
├── run_demo.sh               # scripted end-to-end demo
├── db/init.sql               # PostGIS schema + demo zones/resources
├── simulator/                # fake sensor feed -> Kafka (sensor.raw)
├── ingestion/                # Kafka -> PostgreSQL
├── prediction/               # anomaly/risk scoring -> risk.events
├── damage/                   # Severity Index (+ segmentation stub) -> damage.scores
├── resource/                 # LP dispatch + Dijkstra routing
├── alert/                    # alerts REST + WebSocket
├── gateway/                  # API key auth, rate limiting, routing
├── web/index.html            # dashboard (map, alerts, dispatch plan)
├── ml/                       # XGBoost + U-Net training scripts
├── k8s/                      # namespace, infra, deployments, HPA
├── loadtest/locustfile.py    # surge test for autoscaling
└── tests/test_severity.py    # unit tests (SI worked example = 62.3)
```

## Run in VS Code (no Docker needed)
Requires Python 3.10+ only. Everything runs in one process: Kafka -> in-memory bus, PostgreSQL -> SQLite.
The business logic (Severity Index, risk model, LP dispatch, Dijkstra routing) is the same code the containers use.
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\\Scripts\\activate
pip install -r requirements-local.txt
python run_local.py                  # platform + scripted demo with live logs, then keeps serving
```
Open the dashboard at http://localhost:8000 (Ctrl+C to stop). In VS Code: **Run and Debug** (F5) has ready-made
configurations, and **Terminal > Run Task** has *Install dependencies*, *Run tests*, *Run platform + demo*.
Other commands: `python run_local.py --demo-only`, `python -m pytest -v tests`,
`python ml/make_synthetic_data.py && (cd ml && python train_early_warning.py)`, `python ml/demo_segmentation.py`.
Interactive API docs: http://localhost:8000/docs (use header `x-api-key: change-me-demo-key`).

## Run locally (Docker)
```bash
cp .env.example .env
make demo                 # builds everything + starts simulator
./run_demo.sh             # or watch the dashboard: http://localhost:3000
make test                 # unit tests
```
Gateway: `http://localhost:8000` (send header `x-api-key: change-me-demo-key`).
Example: `GET /api/alert/alerts`, `GET /api/resource/dispatch`, `POST /api/damage/assess`.

## Run on Kubernetes (minikube)
```bash
minikube start
make k8s-build && make k8s-deploy
minikube service gateway-external -n disaster --url
kubectl -n disaster get hpa -w            # watch autoscaling during: locust -f loadtest/locustfile.py
```

## Kafka topics
`sensor.raw` -> `risk.events` / `damage.scores` -> alerts.

## Execution order (see project plan)
1. `make demo` and verify all services. 2. Train models in `ml/` and plug into
`prediction/model.py` and `damage/segmentation.py`. 3. Swap the demo road graph in `resource/routing.py`
for an OSMnx graph. 4. Deploy to Kubernetes and run the load test. 5. Record the demo.
