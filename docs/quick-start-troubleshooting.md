# Quick Start Troubleshooting — LVCA

Самые частые проблемы при первом запуске и их решения.

---

## Диагностика за 30 секунд

```bash
# 1. Проверить статус контейнеров
make ps
# или: docker compose ps

# 2. Проверить здоровье сервисов
make health
# Ожидается: {"status": "ok", "services": {"stt": true, "brain": true, "tts": true}}

# 3. Посмотреть логи всех сервисов
make logs
# или конкретного: docker compose logs brain --tail 50
```

---

## 1. `make setup` не скачивает модели

**Симптом:** `make setup` завершается без ошибок, но `make list-models` показывает пустой список.

**Причина:** Docker-контейнер Ollama не запущен в момент скачивания.

**Решение:**
```bash
# Запустить только Ollama
docker compose up -d ollama

# Подождать 10-15 секунд, затем скачать модели вручную
make pull-models

# Проверить
make list-models
# Ожидается: qwen2.5:7b-instruct-q4_K_M, nomic-embed-text
```

---

## 2. `make health` возвращает `false` для одного или всех сервисов

**Шаг 1: Проверить что контейнеры запущены**
```bash
make ps
# Все контейнеры должны быть в статусе "Up"
```

**Шаг 2: Проверить логи падающего сервиса**
```bash
docker compose logs brain --tail 50
docker compose logs stt --tail 50
docker compose logs tts --tail 50
docker compose logs ollama --tail 50
```

**Шаг 3: Перезапустить проблемный сервис**
```bash
make restart svc=brain
# или
docker compose restart brain
```

---

## 3. Brain не отвечает — Ollama недоступен

**Симптом:** `make health` показывает `"brain": false`. Логи Brain: `Connection refused` или `Ollama timeout`.

**Причина:** Модель не загружена в Ollama, или Ollama ещё загружается.

**Решение:**
```bash
# Проверить доступность Ollama
curl http://localhost:11434/api/tags

# Если пустой ответ — скачать модели
make pull-models

# Если Ollama не отвечает — перезапустить
docker compose restart ollama

# Подождать 30-60 секунд (первый запуск LLM загружает модель в VRAM)
make health
```

---

## 4. STT зависает / не транскрибирует

**Симптом:** Отправка WAV возвращает пустой результат или таймаут.

**Причина A: Модель STT ещё загружается (первый запуск)**
```bash
docker compose logs stt --tail 30
# Ищи: "Loading model..." или "Model loaded"
# Подожди 1-3 минуты при первом запуске (скачивает ~1.5 GB)
```

**Причина B: GPU не виден контейнеру**
```bash
# Проверить доступность GPU
docker compose exec stt nvidia-smi
# Если ошибка — использовать GPU-overlay
make up-gpu
```

**Причина C: WAV в неправильном формате**
```bash
# STT ожидает: 16kHz, mono, int16 PCM
# Проверить формат тестового файла:
ffprobe test.wav
# Конвертировать если нужно:
ffmpeg -i input.wav -ar 16000 -ac 1 -c:a pcm_s16le output.wav
```

---

## 5. TTS не синтезирует речь

**Симптом:** `POST /api/synthesize` возвращает ошибку или пустой WAV.

**Причина A: Piper-модель не скачана**
```bash
docker compose logs tts --tail 30
# Ищи: "Piper model not found" или "FileNotFoundError"
```
```bash
# Скачать TTS модели
make setup
# или вручную:
docker compose exec tts python -c "from engine import download_piper_model; download_piper_model()"
```

**Причина B: XTTS-v2 включён, но нет GPU**
```bash
# Переключиться на Piper (CPU)
# В .env:
TTS_ENGINE=piper
TTS_DEVICE=cpu
# Перезапустить:
docker compose restart tts
```

**Проверка TTS напрямую:**
```bash
curl -X POST http://localhost:8003/api/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Тест"}' \
  --output test.wav && echo "Success" || echo "Failed"
```

---

## 6. Недостаточно VRAM

**Симптом:** Логи Ollama содержат `CUDA out of memory` или `failed to allocate`. LLM работает медленно (< 5 tokens/s).

**Решение A: Использовать меньшую модель**
```env
# В .env:
OLLAMA_MODEL_CHAT=qwen2.5:3b-instruct-q4_K_M
```

**Решение B: Уменьшить STT модель**
```env
STT_MODEL_SIZE=medium
```

**Решение C: CPU-offload для Ollama**
```bash
# Ollama автоматически выгружает слои на CPU когда не хватает VRAM
# Проверить загрузку:
nvidia-smi
```

**Мониторинг VRAM в реальном времени:**
```bash
nvidia-smi -l 2   # обновление каждые 2 секунды
# или: http://localhost:3000 (Grafana)
```

---

## 7. Desktop Agent не подключается

**Симптом:** `make health-desktop` возвращает ошибку. Brain отвечает `Desktop Agent unavailable`.

**Причина A: Desktop Agent не запущен**
```bash
# Запустить в отдельном терминале
make desktop-agent

# Проверить
curl http://localhost:9100/health
```

**Причина B: Зависимости не установлены**
```bash
make desktop-agent-install
# или:
pip install pyautogui pygetwindow pycaw mss plyer psutil GPUtil
```

**Причина C: Антивирус блокирует pyautogui**
```
Добавить исключение для:
- C:\Users\vesna\PycharmProjects\LVCA\desktop_agent\
- python.exe / pythonw.exe
```

**Причина D: Неверный `DESKTOP_AGENT_URL` в Docker**
```env
# В .env (из Docker-контейнера Desktop Agent доступен через host):
DESKTOP_AGENT_URL=http://host.docker.internal:9100
```

---

## 8. Desktop App не запускается

**Симптом:** `make app` падает с ошибкой импорта или сегфолтом.

**Причина A: Зависимости не установлены**
```bash
make app-install
# Устанавливает: customtkinter, pyaudio, sounddevice, httpx, sseclient
```

**Причина B: PyAudio не может найти микрофон**
```bash
python -c "import pyaudio; p = pyaudio.PyAudio(); print(p.get_device_count())"
# Если 0 — проверить настройки микрофона в Windows
```

**Причина C: customtkinter требует Tcl/Tk**
```bash
# Убедиться что Python установлен с tk support
python -c "import tkinter"
# Если ошибка — переустановить Python с "tcl/tk and IDLE" компонентом
```

---

## 9. Контейнер в постоянном restart loop

**Симптом:** `docker compose ps` показывает `Restarting`.

```bash
# Посмотреть причину
docker compose logs <service-name> --tail 100

# Типичные причины:
# 1. Порт уже занят
# 2. .env не существует (cp .env.example .env)
# 3. Неверный путь к модели
# 4. Недостаточно памяти

# Принудительно пересоздать контейнер
docker compose up -d --force-recreate <service>
```

---

## 10. SSE стриминг не работает (ответы не появляются в реальном времени)

**Симптом:** Ответ приходит целиком с задержкой вместо потокового вывода.

**Причина A: Nginx / прокси буферизирует ответ**
```
Добавить заголовок: X-Accel-Buffering: no
```

**Причина B: Desktop App использует REST fallback**
```bash
# Проверить что SSE endpoint доступен
curl -N "http://localhost:8000/api/chat/stream?text=test&session_id=s1"
# Должны идти события data: {...} одно за другим
```

**Причина C: Firewall блокирует долгоживущие соединения**
```
Добавить исключение для localhost:8000 в Windows Firewall
```

---

## 11. RAG не находит релевантные документы

**Симптом:** Brain не использует контекст из базы знаний, хотя документы добавлены.

**Шаг 1: Убедиться что индексация прошла успешно**
```bash
make index-docs
# Должно вывести: "Indexed X chunks from Y documents"
```

**Шаг 2: Проверить Qdrant напрямую**
```bash
curl http://localhost:6333/collections/lvca_knowledge
# Убедиться что vectors_count > 0
```

**Шаг 3: Снизить порог релевантности**
```env
# В .env:
RAG_SCORE_THRESHOLD=0.3   # default: 0.5
```

**Шаг 4: Переиндексировать**
```bash
# Удалить старую коллекцию и переиндексировать
curl -X DELETE http://localhost:6333/collections/lvca_knowledge
make index-docs
```

---

## 12. Ошибки при первой сборке (`make build`)

**Симптом:** `docker compose build` падает при установке зависимостей.

**Причина A: Проблемы с pip/uv в Docker**
```bash
# Попробовать с --no-cache
docker compose build --no-cache brain

# Проверить что Docker Desktop имеет доступ к интернету
```

**Причина B: Конфликт версий Python**
```bash
# Проверить версию Python в Dockerfile
grep "python" services/brain/Dockerfile
# Должна быть 3.11+
```

---

## Таблица кодов ошибок Health Check

| Сервис | HTTP Status | Причина |
|--------|-------------|---------|
| Orchestrator | 503 | Один из сервисов недоступен |
| Brain | 503 | Ollama не отвечает |
| STT | 503 | Whisper модель не загружена |
| TTS | 503 | Piper модель не найдена |
| Desktop Agent | 404 | Сервис не запущен |

---

## Быстрый сброс (когда ничего не помогает)

```bash
# Остановить всё
make down

# Удалить контейнеры и тома (НЕ удаляет скачанные модели Ollama)
docker compose down -v

# Пересобрать с нуля
make build

# Запустить заново
make up

# Проверить
make health
```

**Полный сброс (включая модели):**
```bash
make clean   # ОСТОРОЖНО: удаляет все Docker volumes включая Ollama модели
make setup   # Скачать модели заново (~6.3 GB)
make build && make up
```

---

## Получить помощь

Если проблема не решена:

1. Собрать диагностику:
```bash
docker compose ps > diag.txt
docker compose logs >> diag.txt 2>&1
make health >> diag.txt 2>&1
nvidia-smi >> diag.txt 2>&1
```

2. Проверить `docs/limitations.md` — возможно это известное ограничение
3. Открыть issue на GitHub с содержимым `diag.txt`
