# Конфигурация — LVCA

Вся конфигурация выполняется через переменные окружения в файле `.env`.

```bash
cp .env.example .env
# Отредактируйте .env под свои настройки
```

---

## STT — Распознавание речи

| Переменная | По умолчанию | Варианты | Описание |
|------------|--------------|----------|----------|
| `STT_MODEL_SIZE` | `large-v3-turbo` | `tiny` `base` `small` `medium` `large-v3-turbo` | Размер модели Whisper. Больше = лучше качество, больше VRAM. |
| `STT_DEVICE` | `auto` | `auto` `cuda` `cpu` | `auto` выбирает GPU при наличии. |
| `STT_COMPUTE_TYPE` | `float16` | `float16` `float32` `int8` | `float16` для GPU, `int8` для CPU. |
| `STT_LANGUAGE` | `` (авто) | `ru` `en` ... | Принудительный язык; пусто = автоопределение по аудио. |
| `STT_BEAM_SIZE` | `5` | `1`–`10` | Ширина лучевого поиска. Больше = точнее, медленнее. |
| `STT_MODEL_CACHE` | `/models` | любой путь | Директория для кэша модели Whisper. |
| `STT_VAD_ENABLED` | `true` | `true` `false` | Включить препроцессинг Silero VAD. Рекомендуется: `true`. |
| `STT_VAD_THRESHOLD` | `0.5` | `0.1`–`0.9` | Чувствительность определения голоса. Меньше = чувствительнее. |
| `STT_NO_SPEECH_THRESHOLD` | `0.9` | `0.5`–`1.0` | Подавление «галлюцинированных» транскрипций на тишине. |

**Рекомендуемые конфигурации:**

```env
# Лучшее качество (RTX 3060 12ГБ)
STT_MODEL_SIZE=large-v3-turbo
STT_DEVICE=auto
STT_COMPUTE_TYPE=float16

# Быстрее, меньше VRAM
STT_MODEL_SIZE=medium
STT_COMPUTE_TYPE=float16

# Только CPU (без GPU)
STT_MODEL_SIZE=small
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8
```

---

## LLM — Ollama / Brain

| Переменная | По умолчанию | Варианты | Описание |
|------------|--------------|----------|----------|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | любой URL | URL сервиса Ollama. Для нативного режима: `http://localhost:11434`. |
| `OLLAMA_MODEL_CHAT` | `qwen2.5:7b-instruct-q4_K_M` | любая модель Ollama | LLM для Brain-агента. |
| `OLLAMA_MODEL_EMBED` | `nomic-embed-text` | любая модель эмбеддингов Ollama | Модель эмбеддингов для RAG. |
| `OLLAMA_TEMPERATURE` | `0.2` | `0.0`–`1.0` | Температура LLM. `0.2` = сфокусированный/детерминированный. |
| `OLLAMA_TOP_P` | `0.9` | `0.0`–`1.0` | Nucleus sampling. |
| `OLLAMA_MAX_TOKENS` | `2048` | `256`–`32768` | Максимум токенов на ответ. |
| `OLLAMA_TIMEOUT` | `120` | секунды | Таймаут запроса к LLM. |
| `AGENT_MAX_STEPS` | `8` | `1`–`20` | Максимум итераций ReAct-цикла на запрос. |
| `MEMORY_MAX_MESSAGES` | `20` | `5`–`100` | Размер окна истории разговора. |

**Альтернативные модели:**

```env
# Легче / быстрее (ниже качество)
OLLAMA_MODEL_CHAT=qwen2.5:3b-instruct-q4_K_M

# Лучше качество (больше VRAM: ~8 ГБ)
OLLAMA_MODEL_CHAT=qwen2.5:14b-instruct-q4_K_M

# Более детерминированный вывод
OLLAMA_TEMPERATURE=0.1

# Более креативный
OLLAMA_TEMPERATURE=0.7
```

---

## TTS — Синтез речи

| Переменная | По умолчанию | Варианты | Описание |
|------------|--------------|----------|----------|
| `TTS_ENGINE` | `piper` | `piper` `xtts` | Движок TTS. `piper` = CPU, быстрый. `xtts` = GPU, клонирование голоса. |
| `TTS_DEVICE` | `cpu` | `cpu` `cuda` | Устройство для XTTS-v2. Для Piper игнорируется (всегда CPU). |
| `TTS_LANGUAGE` | `ru` | `ru` `en` ... | Язык синтеза речи. |
| `TTS_VOICE` | `ru_RU-irina-medium` | имя голоса Piper | Файл голосовой модели Piper. |
| `TTS_SPEED` | `1.0` | `0.5`–`2.0` | Множитель скорости речи. |
| `TTS_SAMPLE_RATE` | `22050` | `22050` `44100` | Частота дискретизации выходного аудио (Гц). |
| `XTTS_MODEL_PATH` | `/models/xtts` | любой путь | Путь к файлам модели XTTS-v2. |
| `XTTS_SPEAKER_WAV` | `` | путь к WAV файлу | Референсное аудио для клонирования голоса (только XTTS-v2). |

**Включение клонирования голоса (XTTS-v2):**

```env
TTS_ENGINE=xtts
TTS_DEVICE=cuda
XTTS_SPEAKER_WAV=/path/to/my_voice_sample.wav
```

---

## RAG — Векторное хранилище

| Переменная | По умолчанию | Варианты | Описание |
|------------|--------------|----------|----------|
| `QDRANT_URL` | `http://qdrant:6333` | любой URL | URL сервиса Qdrant. |
| `QDRANT_COLLECTION` | `lvca_knowledge` | любая строка | Имя коллекции в Qdrant. |
| `EMBED_PROVIDER` | `ollama` | `ollama` `hash` | Провайдер эмбеддингов. `hash` = быстрые случайные (только для тестов). |
| `RAG_TOP_K` | `6` | `1`–`20` | Количество извлекаемых чанков на запрос. |
| `RAG_SCORE_THRESHOLD` | `0.5` | `0.0`–`1.0` | Минимальное косинусное сходство для включения чанка. |
| `CHUNK_SIZE` | `800` | `200`–`2000` | Токенов на чанк документа. |
| `CHUNK_OVERLAP` | `120` | `0`–`500` | Перекрытие между соседними чанками. |

---

## Redis — Кэш

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `REDIS_URL` | `redis://redis:6379/0` | URL подключения к Redis. |
| `SESSION_TTL` | `3600` | Время жизни сессии в секундах (1 час). |

---

## URL сервисов (межсервисное взаимодействие)

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `STT_URL` | `http://stt:8001` | URL STT-сервиса (внутри Docker-сети). |
| `BRAIN_URL` | `http://brain:8002` | URL Brain-сервиса. |
| `TTS_URL` | `http://tts:8003` | URL TTS-сервиса. |
| `DESKTOP_AGENT_URL` | `http://host.docker.internal:9100` | URL Desktop Agent (нативный Windows-процесс). |

> Для нативного режима Python (без Docker) используйте `http://localhost:ПОРТ` для всех URL сервисов.

---

## Desktop Agent

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DESKTOP_AGENT_HOST` | `127.0.0.1` | Адрес привязки. Оставьте `127.0.0.1` для безопасности. |
| `DESKTOP_AGENT_PORT` | `9100` | Порт. |
| `DESKTOP_AGENT_PYAUTOGUI_FAILSAFE` | `true` | Переместить мышь в угол для экстренной остановки автоматизации. |
| `DESKTOP_AGENT_PAUSE` | `0.1` | Пауза между действиями pyautogui (секунды). |

---

## Мониторинг

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `LOG_LEVEL` | `INFO` | `DEBUG` `INFO` `WARNING` `ERROR` |
| `GRAFANA_PASSWORD` | `admin` | Пароль администратора Grafana. |
| `PROMETHEUS_PORT` | `9090` | Порт метрик Prometheus. |
| `METRICS_ENABLED` | `true` | Включить сбор метрик Prometheus. |

---

## Полный пример .env

```env
# ── STT ────────────────────────────────────────────
STT_MODEL_SIZE=large-v3-turbo
STT_DEVICE=auto
STT_COMPUTE_TYPE=float16
STT_LANGUAGE=
STT_BEAM_SIZE=5
STT_MODEL_CACHE=/models
STT_VAD_ENABLED=true
STT_VAD_THRESHOLD=0.5
STT_NO_SPEECH_THRESHOLD=0.9

# ── LLM / Ollama ───────────────────────────────────
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL_CHAT=qwen2.5:7b-instruct-q4_K_M
OLLAMA_MODEL_EMBED=nomic-embed-text
OLLAMA_TEMPERATURE=0.2
OLLAMA_TOP_P=0.9
OLLAMA_MAX_TOKENS=2048
OLLAMA_TIMEOUT=120
AGENT_MAX_STEPS=8
MEMORY_MAX_MESSAGES=20

# ── TTS ────────────────────────────────────────────
TTS_ENGINE=piper
TTS_DEVICE=cpu
TTS_LANGUAGE=ru
TTS_VOICE=ru_RU-irina-medium
TTS_SPEED=1.0
TTS_SAMPLE_RATE=22050

# ── RAG / Qdrant ───────────────────────────────────
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=lvca_knowledge
EMBED_PROVIDER=ollama
RAG_TOP_K=6
RAG_SCORE_THRESHOLD=0.5
CHUNK_SIZE=800
CHUNK_OVERLAP=120

# ── Redis ──────────────────────────────────────────
REDIS_URL=redis://redis:6379/0
SESSION_TTL=3600

# ── URL сервисов ────────────────────────────────────
STT_URL=http://stt:8001
BRAIN_URL=http://brain:8002
TTS_URL=http://tts:8003
DESKTOP_AGENT_URL=http://host.docker.internal:9100

# ── Desktop Agent ──────────────────────────────────
DESKTOP_AGENT_HOST=127.0.0.1
DESKTOP_AGENT_PORT=9100
DESKTOP_AGENT_PYAUTOGUI_FAILSAFE=true
DESKTOP_AGENT_PAUSE=0.1

# ── Мониторинг ─────────────────────────────────────
LOG_LEVEL=INFO
GRAFANA_PASSWORD=admin
METRICS_ENABLED=true
```

---

## Конфигурация для нативного режима Python (без Docker)

При запуске через `make native-up` вместо Docker:

```env
OLLAMA_BASE_URL=http://localhost:11434
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379/0
STT_URL=http://localhost:8001
BRAIN_URL=http://localhost:8002
TTS_URL=http://localhost:8003
DESKTOP_AGENT_URL=http://localhost:9100
```

---

## Настройка производительности

### Максимальная скорость (ниже качество)

```env
STT_MODEL_SIZE=medium
STT_BEAM_SIZE=1
OLLAMA_MODEL_CHAT=qwen2.5:3b-instruct-q4_K_M
OLLAMA_MAX_TOKENS=512
```

### Максимальное качество (требуется больше VRAM)

```env
STT_MODEL_SIZE=large-v3-turbo
STT_BEAM_SIZE=5
OLLAMA_MODEL_CHAT=qwen2.5:14b-instruct-q4_K_M
OLLAMA_MAX_TOKENS=4096
TTS_ENGINE=xtts
```

### Режим только CPU (без GPU)

```env
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8
STT_MODEL_SIZE=small
TTS_ENGINE=piper
TTS_DEVICE=cpu
```
