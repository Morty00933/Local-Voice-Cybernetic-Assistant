.PHONY: up down build logs ps health gpu pull-models clean desktop-agent setup app app-install index-docs native-up native-down native-status

# ── First-time setup ─────────────────────────────────────────────
setup:
	python scripts/setup.py

# ── Development ───────────────────────────────────────────────────
up:
	docker compose up -d

up-gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

down:
	docker compose down

build:
	docker compose build

build-gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml build

logs:
	docker compose logs -f

ps:
	docker compose ps

restart:
	docker compose restart $(svc)

# ── Health & Status ───────────────────────────────────────────────
health:
	@curl -s http://localhost:8000/api/health | python -m json.tool

health-stt:
	@curl -s http://localhost:8001/health | python -m json.tool

health-brain:
	@curl -s http://localhost:8002/health | python -m json.tool

health-tts:
	@curl -s http://localhost:8003/health | python -m json.tool

# ── Ollama Models ─────────────────────────────────────────────────
pull-models:
	docker compose exec ollama ollama pull qwen2.5:14b-instruct-q4_K_M
	docker compose exec ollama ollama pull nomic-embed-text

list-models:
	docker compose exec ollama ollama list

# ── Chat ──────────────────────────────────────────────────────────
chat:
	@python -c "import urllib.request,json;msg=input('You: ');req=urllib.request.Request('http://localhost:8000/api/chat',data=json.dumps({'text':msg}).encode(),headers={'Content-Type':'application/json'});res=urllib.request.urlopen(req);print(json.dumps(json.loads(res.read()),indent=2,ensure_ascii=False))"

# ── Kubernetes ────────────────────────────────────────────────────
helm-install:
	helm install lvca infra/helm/lvca/ -f infra/helm/lvca/values.yaml

helm-install-dev:
	helm install lvca infra/helm/lvca/ -f infra/helm/lvca/values-dev.yaml

helm-install-hybrid:
	helm install lvca infra/helm/lvca/ -f infra/helm/lvca/values-hybrid.yaml

helm-upgrade:
	helm upgrade lvca infra/helm/lvca/ -f infra/helm/lvca/values.yaml

helm-uninstall:
	helm uninstall lvca

helm-template:
	helm template lvca infra/helm/lvca/ -f infra/helm/lvca/values.yaml

# ── Desktop Agent (native, outside Docker) ───────────────────────
desktop-agent:
	cd desktop_agent && uv pip install --system -r requirements.txt
	python -m desktop_agent.main

desktop-agent-install:
	cd desktop_agent && uv pip install --system -r requirements.txt

health-desktop:
	@curl -s http://localhost:9100/health | python -m json.tool

# ── RAG Indexing ──────────────────────────────────────────────────
index-docs:
	python scripts/index.py

# ── Desktop App ──────────────────────────────────────────────────
app:
	python -m app.main

app-install:
	uv pip install --system -r app/requirements.txt

# ── Native Mode (without Docker) ─────────────────────────────────
native-up:
	python scripts/native_up.py

native-down:
	python scripts/native_up.py --stop

native-status:
	python scripts/native_up.py --status

native-infra:
	python scripts/native_up.py --infra

# ── Cleanup ───────────────────────────────────────────────────────
clean:
	docker compose down -v --rmi local
