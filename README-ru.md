# LVCA — Local Voice Cybernetic Assistant

**Полностью локальный голосовой ассистент с агентным управлением ПК.**

Работает на RTX 3060 12GB без интернета. Слушает → Думает → Говорит → Действует.

> English version: [README.en.md](README.en.md)

```
Микрофон  ─▶  [STT]  ─▶  [Brain / ReAct Agent]  ─▶  [TTS]  ─▶  Динамик
                                    │
                               [25 Tools]
              browser · code · vision · files · system
                                    │
                           [Desktop Agent]
              apps · windows · input · clipboard · media
```

---

## Быстрый старт (5 минут)

### Требования
| | |
|---|---|
| GPU | NVIDIA RTX 3060 12GB+ (рекомендуется) |
| RAM | 24 GB |
| Диск | ~15 GB для моделей |
| Docker | Docker Desktop (с WSL2 на Windows) |
| Python | 3.11+ (для Desktop App и Desktop Agent) |

### Установка

```bash
# 1. Клонировать репозиторий
git clone <repo-url> && cd LVCA

# 2. Создать конфигурацию
cp .env.example .env

# 3. Скачать все модели (~6.3 GB)
make setup

# 4. Собрать Docker-образы
make build          # CPU
make build-gpu      # GPU (рекомендуется)

# 5. Запустить все сервисы
make up             # CPU
make up-gpu         # GPU

# 6. Проверить готовность
make health
```

Ожидаемый ответ:
```json
{"status": "ok", "services": {"stt": true, "brain": true, "tts": true}}
```

### Первый запрос

```bash
# Текстовый чат в терминале
make chat

# Или через curl
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет! Что ты умеешь?", "session_id": "demo"}'

# Стриминг (токен за токеном)
curl -N "http://localhost:8000/api/chat/stream?text=Привет&session_id=demo"
```

### GUI-клиент

```bash
make app-install   # один раз
make app           # запустить
```

### Jarvis-режим (управление ПК)

```bash
make desktop-agent-install   # один раз
make desktop-agent           # запустить в отдельном терминале
```

---

## Ключевые возможности

| Возможность | Описание |
|-------------|----------|
| **Голосовой чат** | Push-to-talk через Desktop App или WebSocket |
| **Потоковый ответ** | SSE стриминг, токен за токеном |
| **25 инструментов** | Управление ПК, браузер, файлы, код, скриншоты |
| **RAG** | База знаний из .md / .txt / .pdf файлов |
| **100% локально** | Без интернета и облаков |
| **Мониторинг** | Grafana + Prometheus дашборды |
| **Kubernetes** | Helm charts для продакшн-деплоя |

---

## Нейронные сети (5 моделей)

| # | Модель | Задача | VRAM |
|---|--------|--------|------|
| 1 | **Qwen 2.5 7B Q4_K_M** | LLM / ReAct Agent | ~5–7 GB |
| 2 | **Faster Whisper large-v3-turbo** | Речь → текст | ~1.5 GB |
| 3 | **Silero VAD** | Детекция голоса | 0 (CPU) |
| 4 | **Piper VITS (Irina)** | Текст → речь | 0 (CPU) |
| 5 | **nomic-embed-text** | Эмбеддинги (RAG) | ~0.5 GB |
| | | **Итого:** | **~7–9 GB** |

Подробнее: [docs/models.md](docs/models.md)

---

## Архитектура

```
┌──────────────────────────────────────────────────────┐
│               Desktop App (CustomTkinter)             │
│          Чат · Push-to-Talk · Статус сервисов         │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP / SSE / WebSocket
┌───────────────────────▼──────────────────────────────┐
│               Orchestrator  :8000                     │
│        API Gateway · SSE Proxy · WS Manager           │
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
│       Desktop Agent  :9100  (нативный)   │
│  pyautogui · pygetwindow · pycaw · mss   │
└──────────────────────────────────────────┘
```

Подробнее: [docs/architecture.md](docs/architecture.md)

---

## 25 инструментов Brain

| Категория | Инструменты |
|-----------|-------------|
| Система | `system_cmd`, `file_read`, `file_write`, `file_list` |
| Код | `code_gen` |
| Браузер | `browser` (Playwright) |
| Зрение | `vision` (мультимодальный анализ) |
| Приложения | `app_launch`, `app_close`, `app_list` |
| Окна | `window_list`, `window_control` |
| Ввод | `type_text`, `hotkey`, `click`, `scroll` |
| Экран | `screenshot` |
| Буфер | `clipboard_get`, `clipboard_set` |
| Медиа | `volume_control`, `media_control` |
| Процессы | `process_list`, `process_kill` |
| Инфо | `system_info` |
| Уведомления | `notify` |

Подробнее с уровнями опасности: [docs/tools.md](docs/tools.md)

---

## RAG — База знаний

```bash
# Добавить документы
cp my_docs.md manual.pdf knowledge/

# Проиндексировать
make index-docs

# Brain автоматически использует контекст при ответах
```

Поддерживаемые форматы: `.md` `.txt` `.pdf`
Примеры: [examples/rag-examples.md](examples/rag-examples.md)

---

## API

```bash
# Текстовый чат (REST)
POST http://localhost:8000/api/chat
Body: {"text": "...", "session_id": "..."}

# Стриминг (SSE)
GET  http://localhost:8000/api/chat/stream?text=...&session_id=...

# Здоровье сервисов
GET  http://localhost:8000/api/health

# RAG индексация
POST http://localhost:8002/api/index
Body: {"text": "...", "filename": "doc.md"}
```

WebSocket:
```
ws://localhost:8000/ws/voice   # Голосовой цикл (PCM ↔ audio+text)
ws://localhost:8000/ws/chat    # Текстовый чат (JSON ↔ JSON)
ws://localhost:8001/ws/stt     # STT поток (PCM int16 → text)
```

SSE формат:
```
data: {"type": "token", "text": "Привет"}
data: {"type": "tool", "tool": "screenshot", "result": "..."}
data: {"type": "done", "full_text": "Привет мир!"}
```

---

## Конфигурация (.env)

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

# Мониторинг
LOG_LEVEL=INFO
GRAFANA_PASSWORD=admin
```

Полный справочник: [docs/configuration.md](docs/configuration.md)

---

## Make-команды

```bash
# Установка
make setup              # Скачать модели
make build / build-gpu  # Собрать образы

# Запуск
make up / up-gpu        # Запустить
make down               # Остановить
make ps                 # Статус
make logs               # Логи

# Проверка
make health             # Все сервисы
make health-stt / health-brain / health-tts / health-desktop

# Использование
make chat               # Текстовый чат в терминале
make app                # GUI-клиент
make index-docs         # Индексировать RAG

# Desktop Agent
make desktop-agent-install
make desktop-agent

# Ollama
make pull-models
make list-models

# Kubernetes
make helm-install / helm-install-dev / helm-install-hybrid
make helm-upgrade / helm-uninstall

# Очистка
make clean              # Удалить образы и тома
```

---

## Мониторинг

| Сервис | URL | Учётные данные |
|--------|-----|----------------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |

Метрики: Request Rate · Error Rate · STT/Brain/TTS Latency P95 · VRAM · CPU/RAM · Active WS Sessions

---

## Kubernetes

```bash
# Production (GPU)
helm install lvca infra/helm/lvca/ -f infra/helm/lvca/values.yaml

# Development (CPU)
helm install lvca infra/helm/lvca/ -f infra/helm/lvca/values-dev.yaml

# Hybrid (Ollama/Qdrant/Redis на хосте)
helm install lvca infra/helm/lvca/ -f infra/helm/lvca/values-hybrid.yaml
```

---

## Производительность

| Этап | Время |
|------|-------|
| STT (Whisper large-v3-turbo) | ~0.5–1.5 с |
| LLM без инструментов | ~2–5 с |
| LLM с цепочкой инструментов | ~5–20 с |
| TTS (Piper, CPU) | ~0.1–0.5 с |
| **Полный цикл речь → ответ** | **~3–7 с** |

---

## Добавить новый инструмент

```python
# services/brain/tools/my_tool.py
from .base import BaseTool, ToolResult

class MyTool(BaseTool):
    name = "my_tool"
    description = "Описание для LLM"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, output="результат")
```

Зарегистрировать в `services/brain/tools/__init__.py` и передать в `Agent`.

---

## Структура проекта

```
LVCA/
├── shared/              # Общие модули (config, logging)
├── services/
│   ├── stt/             # Faster Whisper + Silero VAD
│   ├── brain/           # Qwen Agent + RAG + 25 tools
│   └── tts/             # Piper VITS / XTTS-v2
├── orchestrator/        # API Gateway
├── app/                 # Desktop GUI (CustomTkinter)
├── desktop_agent/       # Нативный Windows-агент
├── scripts/             # setup.py, index.py, native_up.py
├── knowledge/           # Документы для RAG
├── infra/helm/          # Kubernetes Helm Charts
├── monitoring/          # Prometheus + Grafana
├── docs/                # Документация
└── examples/            # Примеры использования
```

---

## Документация

| Файл | Содержание |
|------|-----------|
| [docs/architecture.md](docs/architecture.md) | Схемы, роли компонентов, потоки данных |
| [docs/models.md](docs/models.md) | Все 5 моделей + опциональные, VRAM, выбор |
| [docs/tools.md](docs/tools.md) | 25 инструментов + описания + уровни опасности |
| [docs/configuration.md](docs/configuration.md) | Все .env-параметры с дефолтами |
| [docs/quick-start-troubleshooting.md](docs/quick-start-troubleshooting.md) | Частые ошибки и решения |
| [docs/limitations.md](docs/limitations.md) | Честные ограничения проекта |
| [examples/voice-commands.md](examples/voice-commands.md) | Примеры голосовых команд |
| [examples/desktop-control-examples.md](examples/desktop-control-examples.md) | Примеры управления ПК |
| [examples/rag-examples.md](examples/rag-examples.md) | Примеры работы с базой знаний |
| [USAGE.md](USAGE.md) | Подробная инструкция, API-примеры, проверка |

---

## Стек технологий

| Слой | Технология |
|------|-----------|
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

## Целевое железо

| Компонент | Спецификация |
|-----------|-------------|
| GPU | NVIDIA RTX 3060 12GB |
| RAM | 24 GB |
| CPU | Intel i7-12650H |
| OS | Windows 11 / WSL2 / Linux |
| Docker | Docker Desktop (WSL2 backend) |

---

## Лицензия

Private project.
