# LVCA — Local Voice Cybernetic Assistant

**A fully local voice assistant with agentic PC control.**

Runs on RTX 3060 12GB with no internet. Listens → Thinks → Speaks → Acts.

> Russian version: [README.md](README.md)

```
Microphone  ─▶  [STT]  ─▶  [Brain / ReAct Agent]  ─▶  [TTS]  ─▶  Speaker
                                      │
                                 [25 Tools]
                browser · code · vision · files · system
                                      │
                            [Desktop Agent]
                apps · windows · input · clipboard · media
```

---

## Quick Start (5 minutes)

### Requirements

| | |
|---|---|
| GPU | NVIDIA RTX 3060 12GB+ (recommended) |
| RAM | 24 GB |
| Disk | ~15 GB for models |
| Docker | Docker Desktop (WSL2 on Windows) |
| Python | 3.11+ (for Desktop App and Desktop Agent) |

### Installation

```bash
# 1. Clone the repository
git clone <repo-url> && cd LVCA

# 2. Create configuration
cp .env.example .env

# 3. Download all models (~6.3 GB)
make setup

# 4. Build Docker images
make build          # CPU
make build-gpu      # GPU (recommended)

# 5. Start all services
make up             # CPU
make up-gpu         # GPU

# 6. Check readiness
make health
```

Expected response:
```json
{"status": "ok", "services": {"stt": true, "brain": true, "tts": true}}
```

### First Request

```bash
# Text chat in terminal
make chat

# Or via curl
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello! What can you do?", "session_id": "demo"}'

# Streaming (token by token)
curl -N "http://localhost:8000/api/chat/stream?text=Hello&session_id=demo"
```

### GUI Client

```bash
make app-install   # once
make app           # launch
```

### Jarvis Mode (PC control)

```bash
make desktop-agent-install   # once
make desktop-agent           # run in a separate terminal
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Voice chat** | Push-to-talk via Desktop App or WebSocket |
| **Streaming response** | SSE streaming, token by token |
| **25 tools** | PC control, browser, files, code, screenshots |
| **RAG** | Knowledge base from .md / .txt / .pdf files |
| **100% local** | No internet, no cloud |
| **Monitoring** | Grafana + Prometheus dashboards |
| **Kubernetes** | Helm charts for production deployment |

---

## Neural Networks (5 models)

| # | Model | Task | VRAM |
|---|-------|------|------|
| 1 | **Qwen 2.5 7B Q4_K_M** | LLM / ReAct Agent | ~5–7 GB |
| 2 | **Faster Whisper large-v3-turbo** | Speech → Text | ~1.5 GB |
| 3 | **Silero VAD** | Voice activity detection | 0 (CPU) |
| 4 | **Piper VITS (Irina)** | Text → Speech | 0 (CPU) |
| 5 | **nomic-embed-text** | Embeddings (RAG) | ~0.5 GB |
| | | **Total:** | **~7–9 GB** |

More details: [docs/models.md](docs/models.md)

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│               Desktop App (CustomTkinter)             │
│           Chat · Push-to-Talk · Service Status        │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP / SSE / WebSocket
┌───────────────────────▼──────────────────────────────┐
│               Orchestrator  :8000                     │
│         API Gateway · SSE Proxy · WS Manager          │
└──────┬─────────────────┬─────────────────┬───────────┘
       │                 │                 │
┌──────▼──────┐  ┌───────▼───────┐  ┌─────▼──────┐
│  STT :8001  │  │  Brain :8002  │  │  TTS :8003 │
│   Whisper   │  │   Qwen 7B     │  │   Piper    │
│ + Silero VAD│  │ ReAct · RAG   │  │   VITS     │
│             │  │  25 tools     │  │            │
└─────────────┘  └───────┬───────┘  └────────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
      ┌─────▼────┐ ┌─────▼────┐ ┌────▼────┐
      │  Ollama  │ │  Qdrant  │ │  Redis  │
      │  :11434  │ │  :6333   │ │  :6379  │
      └──────────┘ └──────────┘ └─────────┘

┌──────────────────────────────────────────┐
│    Desktop Agent  :9100  (native process) │
│  pyautogui · pygetwindow · pycaw · mss   │
└──────────────────────────────────────────┘
```

Full details: [docs/architecture.md](docs/architecture.md)

---

## 25 Brain Tools

| Category | Tools |
|----------|-------|
| System | `system_cmd`, `file_read`, `file_write`, `file_list` |
| Code | `code_gen` |
| Browser | `browser` (Playwright) |
| Vision | `vision` (multimodal analysis) |
| Applications | `app_launch`, `app_close`, `app_list` |
| Windows | `window_list`, `window_control` |
| Input | `type_text`, `hotkey`, `click`, `scroll` |
| Screen | `screenshot` |
| Clipboard | `clipboard_get`, `clipboard_set` |
| Media | `volume_control`, `media_control` |
| Processes | `process_list`, `process_kill` |
| Info | `system_info` |
| Notifications | `notify` |

With danger levels: [docs/tools.md](docs/tools.md)

---

## RAG — Knowledge Base

```bash
# Add documents
cp my_docs.md manual.pdf knowledge/

# Index them
make index-docs

# Brain automatically uses context when answering
```

Supported formats: `.md` `.txt` `.pdf`
Examples: [examples/rag-examples.md](examples/rag-examples.md)

---

## API

```bash
# Text chat (REST)
POST http://localhost:8000/api/chat
Body: {"text": "...", "session_id": "..."}

# Streaming (SSE)
GET  http://localhost:8000/api/chat/stream?text=...&session_id=...

# Service health
GET  http://localhost:8000/api/health

# RAG indexing
POST http://localhost:8002/api/index
Body: {"text": "...", "filename": "doc.md"}
```

WebSocket:
```
ws://localhost:8000/ws/voice   # Voice loop (PCM ↔ audio+text)
ws://localhost:8000/ws/chat    # Text chat (JSON ↔ JSON)
ws://localhost:8001/ws/stt     # STT stream (PCM int16 → text)
```

SSE format:
```
data: {"type": "token", "text": "Hello"}
data: {"type": "tool", "tool": "screenshot", "result": "..."}
data: {"type": "done", "full_text": "Hello world!"}
```

---

## Configuration (.env)

```env
# STT
STT_MODEL_SIZE=large-v3-turbo   # tiny|base|small|medium|large-v3-turbo
STT_DEVICE=auto                  # auto|cuda|cpu

# LLM
OLLAMA_MODEL_CHAT=qwen2.5:7b-instruct-q4_K_M
OLLAMA_TEMPERATURE=0.2

# TTS
TTS_ENGINE=piper                 # piper|xtts
TTS_DEVICE=cpu

# RAG
QDRANT_COLLECTION=lvca_knowledge
EMBED_PROVIDER=ollama

# Monitoring
LOG_LEVEL=INFO
GRAFANA_PASSWORD=admin
```

Full reference: [docs/configuration.md](docs/configuration.md)

---

## Make Commands

```bash
# Setup
make setup              # Download models
make build / build-gpu  # Build images

# Run
make up / up-gpu        # Start services
make down               # Stop services
make ps                 # Container status
make logs               # View logs

# Health checks
make health             # All services
make health-stt / health-brain / health-tts / health-desktop

# Usage
make chat               # Terminal chat
make app                # GUI client
make index-docs         # Index RAG documents

# Desktop Agent
make desktop-agent-install
make desktop-agent

# Ollama
make pull-models
make list-models

# Kubernetes
make helm-install / helm-install-dev / helm-install-hybrid
make helm-upgrade / helm-uninstall

# Cleanup
make clean              # Remove images and volumes
```

---

## Monitoring

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |

Metrics: Request Rate · Error Rate · STT/Brain/TTS Latency P95 · VRAM · CPU/RAM · Active WS Sessions

---

## Kubernetes

```bash
# Production (GPU)
helm install lvca infra/helm/lvca/ -f infra/helm/lvca/values.yaml

# Development (CPU)
helm install lvca infra/helm/lvca/ -f infra/helm/lvca/values-dev.yaml

# Hybrid (Ollama/Qdrant/Redis on host)
helm install lvca infra/helm/lvca/ -f infra/helm/lvca/values-hybrid.yaml
```

---

## Performance

| Stage | Time |
|-------|------|
| STT (Whisper large-v3-turbo) | ~0.5–1.5 s |
| LLM without tools | ~2–5 s |
| LLM with tool chain | ~5–20 s |
| TTS (Piper, CPU) | ~0.1–0.5 s |
| **Full cycle speech → response** | **~3–7 s** |

---

## Adding a New Tool

```python
# services/brain/tools/my_tool.py
from .base import BaseTool, ToolResult

class MyTool(BaseTool):
    name = "my_tool"
    description = "Description for the LLM"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, output="result")
```

Register in `services/brain/tools/__init__.py` and pass to `Agent`.

---

## Project Structure

```
LVCA/
├── shared/              # Shared modules (config, logging)
├── services/
│   ├── stt/             # Faster Whisper + Silero VAD
│   ├── brain/           # Qwen Agent + RAG + 25 tools
│   └── tts/             # Piper VITS / XTTS-v2
├── orchestrator/        # API Gateway
├── app/                 # Desktop GUI (CustomTkinter)
├── desktop_agent/       # Native Windows agent
├── scripts/             # setup.py, index.py, native_up.py
├── knowledge/           # RAG documents
├── infra/helm/          # Kubernetes Helm Charts
├── monitoring/          # Prometheus + Grafana
├── docs/                # Documentation
└── examples/            # Usage examples
```

---

## Documentation

| File | Content |
|------|---------|
| [docs/architecture.md](docs/architecture.md) | Diagrams, component roles, data flows |
| [docs/models.md](docs/models.md) | All 5 models + optional, VRAM, rationale |
| [docs/tools.md](docs/tools.md) | 25 tools + descriptions + danger levels |
| [docs/configuration.md](docs/configuration.md) | All .env parameters with defaults |
| [docs/quick-start-troubleshooting.md](docs/quick-start-troubleshooting.md) | Common errors and fixes |
| [docs/limitations.md](docs/limitations.md) | Honest project limitations |
| [examples/voice-commands.md](examples/voice-commands.md) | Voice command examples |
| [examples/desktop-control-examples.md](examples/desktop-control-examples.md) | PC control examples |
| [examples/rag-examples.md](examples/rag-examples.md) | Knowledge base examples |
| [USAGE.md](USAGE.md) | Detailed guide, API examples, verification |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Qwen 2.5 7B (Ollama / llama.cpp) |
| STT | Faster Whisper (CTranslate2) |
| VAD | Silero VAD (ONNX) |
| TTS | Piper VITS / XTTS-v2 (Coqui) |
| Embeddings | nomic-embed-text (Ollama) |
| Vector DB | Qdrant |
| Cache | Redis |
| API | FastAPI + Uvicorn |
| Streaming | SSE + WebSocket |
| Desktop | pyautogui · pygetwindow · pycaw · mss |
| Browser | Playwright (Chromium) |
| GUI | CustomTkinter |
| Packages | uv |
| Containers | Docker + Docker Compose |
| Orchestration | Kubernetes + Helm |
| Monitoring | Prometheus + Grafana |
| Logging | structlog |

---

## Target Hardware

| Component | Specification |
|-----------|--------------|
| GPU | NVIDIA RTX 3060 12GB |
| RAM | 24 GB |
| CPU | Intel i7-12650H |
| OS | Windows 11 / WSL2 / Linux |
| Docker | Docker Desktop (WSL2 backend) |

---

## License

Private project.
