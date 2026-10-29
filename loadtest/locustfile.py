# Run: locust -f loadtest/locustfile.py --host http://localhost:8000
from locust import HttpUser, task, between

class Citizen(HttpUser):
    wait_time = between(0.1, 0.5)
    headers = {"x-api-key": "change-me-demo-key"}

    @task(3)
    def alerts(self): self.client.get("/api/alert/alerts", headers=self.headers)

    @task(1)
    def dispatch(self): self.client.get("/api/resource/dispatch", headers=self.headers)
