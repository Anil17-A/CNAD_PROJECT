.PHONY: up demo down logs test k8s-build k8s-deploy k8s-down
up:        ; docker compose up -d --build
demo:      ; docker compose --profile demo up -d --build   # includes the sensor simulator
down:      ; docker compose --profile demo down -v
logs:      ; docker compose logs -f --tail=50
test:      ; pip install -q pytest && pytest -q tests
SERVICES = ingestion prediction damage resource alert gateway
k8s-build: ; for s in $(SERVICES); do docker build -t disaster/$$s:latest ./$$s; done; \
             minikube image load $(addprefix disaster/,$(addsuffix :latest,$(SERVICES))) 2>/dev/null || true
k8s-deploy:
	kubectl apply -f k8s/00-namespace.yaml
	kubectl -n disaster create configmap db-init --from-file=db/init.sql --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f k8s/10-infra.yaml -f k8s/20-services.yaml -f k8s/30-hpa.yaml -f k8s/40-gateway-nodeport.yaml
k8s-down:  ; kubectl delete namespace disaster
