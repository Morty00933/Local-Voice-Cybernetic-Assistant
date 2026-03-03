# Voice Commands — Примеры голосовых команд

Всё что можно сказать или напечатать в LVCA. Для Desktop-команд нужен запущенный Desktop Agent.

---

## Базовый разговор

```
"Привет! Как тебя зовут?"
→ Меня зовут LVCA — Local Voice Cybernetic Assistant. Я твой локальный помощник.

"Что ты умеешь?"
→ Я могу управлять приложениями, окнами, файлами, браузером, делать скриншоты,
  управлять громкостью, выполнять код и отвечать на вопросы из базы знаний.

"На каком железе ты работаешь?"
→ RTX 3060 12GB, i7-12650H, 24 GB RAM. Все вычисления происходят локально.

"Сколько инструментов у тебя есть?"
→ 25 инструментов: управление приложениями, окнами, вводом, файлами,
  браузером, скриншотами, буфером обмена, медиа, процессами и системой.
```

---

## Системные вопросы

```
"Сколько сейчас памяти занято?"
→ [вызывает system_info]
  CPU: 23%, RAM: 11.2 / 24 GB (47%), GPU VRAM: 8.1 / 12 GB

"Какие программы сейчас запущены?"
→ [вызывает app_list]
  Chrome (3 окна), VS Code, Telegram, Discord, ...

"Покажи активные процессы"
→ [вызывает process_list]
  PID 1234 — chrome.exe (2.1% CPU, 450 MB RAM)
  PID 5678 — code.exe (0.8% CPU, 280 MB RAM)
  ...
```

---

## Управление приложениями

Требуется Desktop Agent.

```
"Открой Chrome"
→ [app_launch: chrome] Chrome запущен

"Открой VS Code"
→ [app_launch: vscode] VS Code запущен

"Открой проводник"
→ [app_launch: explorer] Проводник открыт

"Закрой Notepad"
→ [app_close: notepad] Notepad закрыт

"Запусти калькулятор"
→ [app_launch: calc] Калькулятор открыт

"Открой Telegram"
→ [app_launch: telegram] Telegram запущен
```

---

## Управление окнами

Требуется Desktop Agent.

```
"Сверни все окна"
→ [hotkey: win+d] Все окна свёрнуты

"Разверни Chrome на весь экран"
→ [window_control: Chrome, maximize] Готово

"Переключись на VS Code"
→ [window_control: VS Code, focus] VS Code на переднем плане

"Поставь Chrome в левую половину экрана"
→ [window_control: Chrome, move x=0, y=0]
  [window_control: Chrome, resize width=960, height=1080]
  Готово

"Закрой все окна Chrome"
→ [window_control: Chrome, close] Все окна Chrome закрыты
```

---

## Поиск и браузер

```
"Найди в интернете: последние новости о Python 3.13"
→ [browser: search "python 3.13 news"]
  Нашёл 5 результатов. Python 3.13 вышел в октябре 2024...

"Открой GitHub"
→ [browser: open https://github.com] GitHub открыт в браузере

"Найди документацию по FastAPI"
→ [browser: search "FastAPI documentation"]
  Официальная документация: https://fastapi.tiangolo.com
  Описание: FastAPI — современный веб-фреймворк для Python...

"Что такое Qdrant?"
→ [browser: search "Qdrant vector database"]
  Qdrant — высокопроизводительная векторная база данных для семантического поиска...
```

---

## Работа с файлами

```
"Прочитай файл README.md"
→ [file_read: README.md] [содержимое файла]

"Покажи все Python файлы в текущей папке"
→ [file_list: ., *.py]
  agent.py, memory.py, prompts.py, vectorstore.py...

"Создай файл todo.txt с текстом 'Купить молоко, хлеб, яйца'"
→ [file_write: todo.txt] Файл создан

"Запиши результаты встречи в meeting_notes.md"
→ [file_write: meeting_notes.md] Файл сохранён

"Найди все JSON файлы на рабочем столе"
→ [file_list: C:\\Users\\vesna\\Desktop, *.json]
  config.json, data.json
```

---

## Управление вводом

Требуется Desktop Agent. Используй осторожно!

```
"Напечатай 'Hello, World!'"
→ [type_text: "Hello, World!"] Текст введён в активное поле

"Нажми Ctrl+C"
→ [hotkey: ctrl+c] Выполнено

"Нажми Ctrl+Z"
→ [hotkey: ctrl+z] Отмена выполнена

"Прокрути страницу вниз"
→ [scroll: down, amount=5] Прокрутка выполнена

"Нажми Enter"
→ [hotkey: enter] Выполнено
```

---

## Скриншоты

Требуется Desktop Agent.

```
"Сделай скриншот экрана"
→ [screenshot: fullscreen → screenshot_20241201_143022.png] Скриншот сохранён

"Скриншот окна Chrome"
→ [screenshot: window=Chrome → chrome_screenshot.png] Готово

"Что ты видишь на экране?"
→ [screenshot] → [vision: опиши что на экране]
  На экране открыт браузер Chrome с сайтом GitHub. Слева — список репозиториев...

"Прочитай текст с этого скриншота"
→ [vision: извлеки текст] На скриншоте написано: "LVCA — Local Voice Cybernetic Assistant..."
```

---

## Буфер обмена

Требуется Desktop Agent.

```
"Что сейчас в буфере обмена?"
→ [clipboard_get] В буфере: "def hello_world(): print('Hello!')"

"Скопируй текст 'print(Hello World)' в буфер"
→ [clipboard_set: "print(Hello World)"] Скопировано в буфер обмена

"Прочитай что я скопировал и объясни"
→ [clipboard_get] → [LLM объясняет содержимое]
```

---

## Медиа и звук

Требуется Desktop Agent.

```
"Громкость 50%"
→ [volume_control: set 50] Громкость установлена 50%

"Выключи звук"
→ [volume_control: mute] Звук выключен

"Включи звук"
→ [volume_control: unmute] Звук включён

"Поставь музыку на паузу"
→ [media_control: play_pause] Пауза

"Следующий трек"
→ [media_control: next] Следующий трек

"Какая сейчас громкость?"
→ [volume_control: get] Текущая громкость: 65%
```

---

## Написание кода

```
"Напиши функцию на Python для сортировки словаря по значению"
→ [code_gen: python]
  def sort_dict_by_value(d, reverse=False):
      return dict(sorted(d.items(), key=lambda x: x[1], reverse=reverse))

"Сгенерируй SQL запрос для выборки пользователей старше 18 лет"
→ [code_gen: sql]
  SELECT * FROM users WHERE age > 18;

"Объясни что делает этот код: lambda x: x[1]"
→ lambda x: x[1] — это анонимная функция, которая принимает итерируемый объект
  и возвращает его второй элемент (с индексом 1)...

"Напиши Bash скрипт для бэкапа директории"
→ [code_gen: bash]
  #!/bin/bash
  SOURCE="$1"
  BACKUP_DIR="$HOME/backups"
  ...
```

---

## Многошаговые задачи

Примеры цепочек инструментов (несколько tool calls за один запрос).

```
"Открой Chrome, перейди на GitHub и сделай скриншот"
→ Step 1: [app_launch: chrome] Открываю Chrome
  Step 2: [browser: open https://github.com] Перехожу на GitHub
  Step 3: [screenshot: fullscreen] Делаю скриншот
  Скриншот сохранён: github_20241201_143500.png

"Проверь сколько RAM, если больше 80% — скажи мне об этом"
→ Step 1: [system_info] CPU: 12%, RAM: 19.8/24 GB (82%)
  RAM использование 82% — превышает порог 80%. Рекомендую закрыть лишние приложения.

"Создай файл report.md, напиши в нём текущее состояние системы и сохрани"
→ Step 1: [system_info] → CPU: 23%, RAM: 11.2 GB, VRAM: 8.1 GB
  Step 2: [file_write: report.md] Создаю файл с данными
  Файл report.md создан. Записал: CPU 23%, RAM 11.2/24 GB, GPU VRAM 8.1/12 GB.

"Найди все .log файлы, прочитай последний и скажи если там есть ошибки"
→ Step 1: [file_list: ., *.log] → app.log, error.log, debug.log
  Step 2: [file_read: error.log]
  Step 3: [LLM анализирует]
  В файле error.log найдено 3 строки с ERROR: Connection timeout на строках 45, 67, 89.
```

---

## Уведомления

Требуется Desktop Agent.

```
"Напомни мне через 5 минут про встречу"
→ [notify: title="LVCA", message="Напоминание: встреча через 5 минут"]
  Уведомление отправлено (используй системный таймер для задержки)

"Покажи уведомление: задача выполнена"
→ [notify: "Задача выполнена"] Уведомление показано
```

---

## Советы для голосового ввода

**Говори чётко и конкретно:**
```
✅ "Открой Chrome и перейди на github.com"
✅ "Создай файл notes.txt с текстом 'список задач'"
✅ "Установи громкость 40 процентов"

❌ "Сделай что-нибудь с интернетом"   ← слишком расплывчато
❌ "Ну открой там... ну знаешь"         ← нет конкретики
```

**Для Desktop-команд убедись что Desktop Agent запущен:**
```bash
make desktop-agent   # в отдельном терминале
make health-desktop  # проверить
```

**Ошибки LLM — переформулируй:**
```
Если LVCA неправильно понял → скажи точнее
"Я имел в виду закрыть Chrome, а не Firefox"
"Нет, нужно прочитать файл по пути C:\notes.txt"
```
