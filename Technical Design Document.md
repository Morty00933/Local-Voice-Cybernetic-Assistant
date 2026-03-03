### 1. Обзор проекта (Project Overview)

**Название**: Local Voice Cybernetic Assistant (LVCA)  
**Тип**: Pet-проект для изучения кибернетики, локальных LLM и агентных систем  
**Цель**: Создать автономного голосового ассистента, который работает 100% локально, понимает речь, отвечает голосом, выполняет действия на ПК и поддерживает продвинутые сценарии (уровень 3).  
**Ключевые принципы**:
- Полная приватность (нет облака, интернета для inference)
- Модульность (три микросервиса)
- Кибернетическая петля: вход (сенсоры) → обработка (мозг) → выход (актуаторы) → обратная связь
- Аппаратная база: RTX 3060 12 ГБ VRAM, 24 ГБ RAM, i7-12650H

**Уровни функциональности** (фокус на уровне 3):
- Уровень 1–2: голосовой чат, системные команды, файлы, RAG
- Уровень 3: управление браузером, кодинг-помощник, голосовое клонирование, анализ экрана/изображений

### 2. Цели и нефункциональные требования (Goals & NFRs)

**Функциональные цели уровня 3**:
- Управление браузером (открытие, поиск, извлечение заголовков/текста)
- Кодинг-помощник (генерация кода, объяснение ошибок, тесты)
- Голосовое клонирование (fine-tune на 5–40 мин записи пользователя)
- Мультимодальность (описание скриншотов, чтение текста с экрана/фото)

**Нефункциональные требования**:
- Latency полного цикла (речь → действие → речь): ≤ 5–7 с в среднем
- VRAM потребление: ≤ 10–11 ГБ в пике
- Скорость LLM: ≥ 25–40 токенов/с
- Безопасность: sandbox для агента (whitelist действий, запрет опасных команд)
- Масштабируемость: легко добавлять новые tools
- Надёжность: fallback на текст при ошибках голоса

### 3. Высокоуровневая архитектура (High-Level Architecture)

Система состоит из трёх независимых микросервисов + оркестратора.

**Компоненты и их взаимодействие**:

1. **Service 1 — Sensory Input (STT + Wake-word)**  
   Вход: микрофон (real-time streaming)  
   Выход: текст + метаданные (confidence, язык)  
   Технология: Faster-Whisper-large-v3-turbo или Parakeet-TDT (CUDA)

2. **Service 2 — Central Brain (LLM + Agent + Tools)**  
   Вход: текст от STT  
   Выход: текст ответа +/– список действий (tool calls)  
   Ядро: Mistral-Nemo-Instruct-2407 12B или Qwen2.5-14B-Instruct (Q4_K_M / Q5_K_M) через Ollama или llama.cpp  
   Агент: LangGraph / ReAct-style с memory (conversation buffer + summary)  
   Tools уровня 3: browser_control, code_generator, vision_analyzer

3. **Service 3 — Actuator Output (TTS + Executor)**  
   Вход: текст + команды  
   Выход: аудио (речь) + выполненные действия на ПК  
   TTS: XTTS-v2 или F5-TTS (с клонированием) + Piper как fallback  
   Executor: Python-функции (subprocess, pyautogui, playwright)

**Оркестратор** (главный процесс):  
- Управляет потоком: запись → STT → LLM → TTS/Executor  
- WebSocket / FastAPI для real-time  
- Docker Compose для деплоя

**Схема данных** (поток):  
Микрофон → [audio chunk] → STT → [text] → LLM Agent → [response text + tool calls] → TTS/Executor → [speech + action]

### 4. Детальный дизайн компонентов уровня 3

#### 4.1. Browser Control Tool
- Функции: открыть URL, выполнить поиск, извлечь title / первые результаты / текст блока, сделать скриншот страницы
- Реализация: Playwright (chromium, headless=false для видимости)
- Интеграция: tool call → JSON-параметры (url, query, action)
- Ограничения: нет авторизации, нет капчи, нет сложного JS без ожидания

#### 4.2. Coding Assistant Tool
- Функции: generate code (по языку + задаче), explain code/error, generate tests
- Реализация: отдельный prompt для LLM (code-only output) + опционально flake8/ruff валидация
- Выход: текст кода → TTS зачитывает + опция сохранения в файл
- Ограничения: не видит IDE, не отлаживает в runtime

#### 4.3. Voice Cloning
- Подход: zero-shot / few-shot cloning (XTTS-v2 / F5-TTS)
- Процесс: пользователь записывает 5–40 мин → сохраняется reference wav → при синтезе указывается speaker_wav
- Качество: лучше на английском, приемлемо на русском после 20+ мин
- Переключение: команда «говори моим голосом» / «стандартный голос»

#### 4.4. Multimodal / Vision
- Функции: describe screenshot, read text from image, answer questions about visual content
- Реализация: LLaVA-1.6-13B или Qwen2.5-VL-7B (через transformers или Ollama если поддерживается)
- Интеграция: pyautogui.screenshot() → base64 → vision model → текст → TTS
- Ограничения: статичные изображения, не видео в реальном времени

### 5. Технологический стек (Tech Stack 2026)

| Слой              | Технология / Модель                          | Почему выбрано                              |
|-------------------|----------------------------------------------|---------------------------------------------|
| STT               | Faster-Whisper-large-v3-turbo / Parakeet     | Лучшее качество + скорость на RTX 3060      |
| LLM / Agent       | Mistral-Nemo 12B / Qwen2.5-14B (Q4/Q5)       | Баланс качество/скорость/русский            |
| TTS               | XTTS-v2 / F5-TTS + Piper fallback            | Клонирование + стабильность                 |
| Vision            | LLaVA-1.6 или Qwen2.5-VL                     | Хорошее понимание экрана/изображений        |
| Browser           | Playwright                                   | Надёжнее Selenium, async, скриншоты         |
| Агент фреймворк   | LangGraph + LangChain tools                  | Гибкость, memory, streaming                 |
| API / Оркестрация | FastAPI + WebSockets                         | Real-time голос                             |
| Контейнеризация   | Docker + Docker Compose                      | Изоляция, воспроизводимость                 |
| Мониторинг        | nvidia-smi, logging, htop                    | Контроль VRAM/CPU                           |