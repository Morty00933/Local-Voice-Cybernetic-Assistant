# LVCA — Инструкция по использованию и проверке

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                        Desktop App (app/)                       │
│            CustomTkinter UI + голосовой ввод/вывод              │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE / WS
┌────────────────────────────▼────────────────────────────────────┐
│                   Orchestrator (:8000)                          │
│        API Gateway — проксирует запросы между сервисами         │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
│  STT :8001  │   │ Brain :8002 │   │  TTS :8003  │
│ Whisper v3  │   │  Qwen 7B +  │   │    Piper    │
│             │   │  25 tools   │   │             │
└─────────────┘   └──────┬──────┘   └─────────────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
        ┌─────▼──┐ ┌────▼───┐ ┌───▼────┐
        │ Ollama │ │ Qdrant │ │ Redis  │
        │:11434  │ │ :6333  │ │ :6379  │
        └────────┘ └────────┘ └────────┘
```

**Компоненты:**
- **STT** — Speech-to-Text (Faster Whisper large-v3-turbo)
- **Brain** — ReAct-агент (Qwen 7B) с 25 tools + RAG
- **TTS** — Text-to-Speech (Piper, русский голос Irina)
- **Orchestrator** — API Gateway, проксирует REST/SSE
- **Desktop Agent** — нативный Windows-агент для управления ПК (порт 9100)
- **Desktop App** — GUI-клиент (CustomTkinter)

---

## 1. Первоначальная установка

### Требования
- **Docker Desktop** (Windows/Mac/Linux)
- **Python 3.11+**
- **NVIDIA GPU** (рекомендуется RTX 3060 12GB+) для STT/Ollama
- ~15 GB свободного места для моделей

### Шаг 1: Скачать модели

```bash
make setup
```

Скрипт автоматически:
1. Запускает `ollama`, `qdrant`, `redis`
2. Скачивает Qwen 2.5 7B (~4.5 GB)
3. Скачивает nomic-embed-text (~270 MB)
4. Скачивает Piper TTS модель (~30 MB)
5. STT модель скачается автоматически при первом запуске контейнера (~1.5 GB)

### Шаг 2: Собрать и запустить все сервисы

```bash
make build    # сборка Docker-образов (первый раз ~15-20 мин)
make up       # запуск всех контейнеров
```

Для GPU-ускорения (Ollama + STT на GPU):
```bash
make build-gpu
make up-gpu
```

### Шаг 3: Проверить здоровье

```bash
make health
```

Ожидаемый вывод:
```json
{
    "status": "ok",
    "services": {
        "brain": true,
        "tts": true,
        "stt": true
    }
}
```

### Шаг 4 (опционально): Установить десктопный клиент

```bash
make app-install   # установить зависимости (customtkinter, pyaudio и т.д.)
```

### Шаг 5 (опционально): Запустить Desktop Agent

Desktop Agent работает нативно на Windows и позволяет Brain управлять ПК:

```bash
make desktop-agent-install
make desktop-agent
```

---

## 2. Ежедневное использование

### Запуск / остановка

```bash
make up       # запустить все сервисы
make down     # остановить все
make ps       # статус контейнеров
make logs     # логи всех сервисов (Ctrl+C для выхода)
```

### Текстовый чат (терминал)

```bash
make chat
# Введите сообщение и нажмите Enter
```

### Текстовый чат (curl)

```bash
# REST запрос
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет, что ты умеешь?", "session_id": "test"}'

# SSE стриминг (токен за токеном)
curl -N "http://localhost:8000/api/chat/stream?text=Привет&session_id=test"
```

### Desktop App (GUI)

```bash
make app
```

Откроется окно с:
- **Чат** — ввод текста, стриминг ответа
- **Микрофон** — удерживайте кнопку для голосового ввода (push-to-talk)
- **Статус-бар** — индикаторы здоровья сервисов

### Голосовой ввод

Через Desktop App:
1. Нажмите и удерживайте кнопку микрофона
2. Говорите
3. Отпустите — голос отправляется на сервер
4. Получите текстовый + голосовой ответ

---

## 3. RAG — работа с базой знаний

### Добавить документы

Положите файлы в `knowledge/`:
```
knowledge/
├── example.md
├── my_docs.txt
└── manual.pdf
```

Поддерживаемые форматы: `.md`, `.txt`, `.pdf`

### Проиндексировать

```bash
make index-docs
```

Документы разбиваются на чанки, векторизуются через nomic-embed-text и сохраняются в Qdrant.

### Проиндексировать через API

```bash
curl -X POST http://localhost:8002/api/index \
  -H "Content-Type: application/json" \
  -d '{"text": "Содержимое документа...", "filename": "doc.md"}'
```

После индексации Brain автоматически использует RAG-контекст при ответах (если релевантность > 0.5).

---

## 4. Возможности Brain (25 tools)

Brain может выполнять команды через Desktop Agent:

| Tool | Описание |
|------|----------|
| `app_launch` | Запуск приложений (Chrome, VS Code и т.д.) |
| `app_close` | Закрытие приложений |
| `app_list` | Список запущенных приложений |
| `web_open` | Открыть URL в браузере |
| `web_search` | Поиск в Google |
| `file_read` | Читать файл |
| `file_write` | Записать файл |
| `file_list` | Список файлов в директории |
| `system_cmd` | Выполнить команду в терминале |
| `screenshot` | Скриншот экрана |
| `clipboard_get/set` | Буфер обмена |
| `volume_set/get` | Управление громкостью |
| `notification` | Показать уведомление |
| ... | и другие |

Пример: скажите "Открой Chrome" — Brain вызовет `app_launch` через Desktop Agent.

---

## 5. Проверка всех компонентов

### Быстрая проверка (все сервисы)

```bash
make health
```

### Проверка каждого сервиса отдельно

```bash
# STT
make health-stt
# или: curl http://localhost:8001/health

# Brain
make health-brain
# или: curl http://localhost:8002/health

# TTS
make health-tts
# или: curl http://localhost:8003/health

# Desktop Agent (если запущен)
make health-desktop
# или: curl http://localhost:9100/health

# Orchestrator
make health
# или: curl http://localhost:8000/api/health
```

### Проверка STT (речь в текст)

```bash
# Отправить WAV файл
curl -X POST http://localhost:8001/api/transcribe \
  -H "Content-Type: audio/wav" \
  --data-binary @test.wav
```

### Проверка Brain (текстовый чат)

```bash
# REST
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Сколько будет 2+2?", "session_id": "test"}'

# SSE стриминг
curl -N "http://localhost:8002/api/chat/stream?text=Привет&session_id=test"
```

### Проверка TTS (текст в речь)

```bash
curl -X POST http://localhost:8003/api/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет, я LVCA"}' \
  --output test_output.wav
# Прослушать test_output.wav
```

### Проверка Ollama (LLM)

```bash
make list-models
# Ожидается: qwen2.5:7b-instruct-q4_K_M, nomic-embed-text
```

### Проверка SSE стриминга (через Orchestrator)

```bash
curl -N "http://localhost:8000/api/chat/stream?text=Расскажи анекдот&session_id=test"
# Ожидается: поток data: {"type":"token","content":"..."} событий
```

### Проверка Desktop Agent

```bash
curl http://localhost:9100/health
# Ожидается: {"status": "ok", "tools": [...]}
```

### Проверка Desktop App

```bash
make app
# 1. Окно должно открыться
# 2. Статус-бар внизу — зелёные точки = сервисы работают
# 3. Введите "Привет" — должен появиться стриминг-ответ
# 4. Нажмите микрофон — должна пойти запись
```

---

## 6. Мониторинг

- **Grafana**: http://localhost:3000 (admin / admin)
- **Prometheus**: http://localhost:9090

---

## 7. Устранение проблем

### Контейнер перезапускается (restart loop)
```bash
docker logs lvca-tts-1 --tail 50    # посмотреть логи
make build                            # пересобрать
docker compose up -d --force-recreate tts  # пересоздать контейнер
```

### Ollama не отвечает
```bash
docker compose restart ollama
make list-models   # проверить что модели скачаны
```

### Нет GPU ускорения
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### Desktop App не подключается
1. Проверьте что сервисы запущены: `make health`
2. Проверьте порт: `curl http://localhost:8000/api/health`
3. Проверьте переменную `LVCA_URL` (по умолчанию `http://localhost:8000`)

### Голос не работает
1. Проверьте TTS: `make health-tts`
2. Проверьте STT: `make health-stt`
3. Убедитесь что микрофон доступен в системе

### Пересборка после изменений кода
```bash
docker compose build --no-cache <service>   # brain, tts, stt, orchestrator
docker compose up -d --force-recreate <service>
```

---

## 8. Полезные команды

```bash
make setup          # первоначальная установка (модели)
make build          # сборка образов
make up             # запуск
make down           # остановка
make ps             # статус
make logs           # логи
make health         # проверка здоровья
make chat           # текстовый чат в терминале
make app            # GUI-клиент
make index-docs     # индексация RAG-документов
make list-models    # список Ollama моделей
make clean          # полная очистка (удаляет тома и образы!)
```
