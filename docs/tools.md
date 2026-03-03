# Tools — LVCA Brain (25 инструментов)

Brain может вызывать до 8 инструментов за один запрос (ReAct-цикл).
Desktop-инструменты требуют запущенного Desktop Agent (:9100).

---

## Уровни опасности

| Уровень | Обозначение | Описание |
|---------|-------------|----------|
| Безопасный | 🟢 safe | Чтение данных, информационные запросы |
| Умеренный | 🟡 moderate | Изменяет состояние, но обратимо |
| Опасный | 🔴 dangerous | Необратимые действия, системные изменения |
| Заблокирован | ⛔ blocked | Всегда отклоняется Desktop Agent |

---

## Системные инструменты

### `system_cmd` — Выполнение команд
🟡 moderate

Выполняет shell-команды через subprocess. Работает только с командами из whitelist.

**Параметры:**
```json
{"command": "dir C:\\Users\\vesna\\Desktop"}
```

**Whitelist команд (примеры):** `dir`, `ls`, `echo`, `python`, `pip`, `git`, `npm`, `type`, `cat`

**Заблокировано:** `format`, `del /s`, `rmdir /s`, `shutdown`, `reg delete`, `netsh`, `sc delete`

**Примеры использования:**
- "Запусти мой Python-скрипт"
- "Покажи список файлов на рабочем столе"
- "Проверь версию Python"

---

### `file_read` — Чтение файла
🟢 safe

Читает содержимое файла и возвращает текст.

**Параметры:**
```json
{"path": "C:\\Users\\vesna\\notes.txt"}
```

**Ограничения:** Доступ только к разрешённым путям (не читает системные файлы Windows, `/etc/`, credentials).

**Примеры:**
- "Прочитай мой файл с заметками"
- "Что написано в README проекта?"

---

### `file_write` — Запись файла
🟡 moderate

Создаёт или перезаписывает файл.

**Параметры:**
```json
{"path": "C:\\Users\\vesna\\output.txt", "content": "текст..."}
```

**Примеры:**
- "Сохрани этот код в файл main.py"
- "Запиши список задач в todo.txt"

---

### `file_list` — Список файлов
🟢 safe

Возвращает список файлов и директорий.

**Параметры:**
```json
{"path": "C:\\Users\\vesna\\Projects", "pattern": "*.py"}
```

**Примеры:**
- "Покажи все Python файлы в проекте"
- "Что есть на рабочем столе?"

---

## Инструменты кода

### `code_gen` — Генерация и выполнение кода
🟡 moderate

Генерирует код через LLM и опционально выполняет его.

**Параметры:**
```json
{
  "language": "python",
  "task": "напиши функцию для сортировки списка",
  "execute": false
}
```

**Поддерживаемые языки:** Python, Bash, JavaScript, PowerShell

**Примеры:**
- "Напиши скрипт для переименования файлов"
- "Сгенерируй SQL запрос для выборки"
- "Объясни эту ошибку и предложи исправление"

---

## Инструменты браузера

### `browser` — Управление браузером
🟡 moderate

Открывает URL, выполняет поиск, извлекает контент страницы. Использует Playwright (Chromium headless).

**Параметры:**
```json
{
  "action": "search",
  "query": "погода в Москве сегодня"
}
```

**Доступные action:**
- `search` — поиск в DuckDuckGo
- `open` — открыть URL
- `extract` — извлечь текст страницы
- `screenshot` — скриншот страницы

**Ограничения:** Нет авторизации, нет CAPTCHA bypass, нет сложного JS.

**Примеры:**
- "Найди документацию по FastAPI"
- "Открой GitHub страницу проекта"
- "Что сейчас происходит в новостях?"

---

## Инструменты зрения

### `vision` — Анализ изображений
🟢 safe

Анализирует скриншоты или изображения через мультимодальную модель (Qwen2.5-VL или LLaVA).

**Параметры:**
```json
{
  "image_path": "screenshot.png",
  "question": "Что написано на экране?"
}
```

**Возможности:** Описание экрана, чтение текста из изображений, ответы на вопросы о visual-контенте.

**Требует:** Мультимодальная модель в Ollama (`ollama pull qwen2.5-vl:7b`)

**Примеры:**
- "Что ты видишь на моём экране?"
- "Прочитай текст с этого скриншота"
- "Опиши что происходит на экране"

---

## Инструменты управления приложениями

Требуют запущенного Desktop Agent.

### `app_launch` — Запуск приложения
🟡 moderate

Запускает приложение по имени или пути.

**Параметры:**
```json
{"app": "chrome"}
```

**Зарегистрированные приложения:** chrome, firefox, vscode, notepad, explorer, telegram, discord, spotify, и другие (настраивается в `desktop_agent/config.py`)

**Примеры:**
- "Открой Chrome"
- "Запусти VS Code"
- "Открой проводник"

---

### `app_close` — Закрытие приложения
🟡 moderate

Закрывает приложение по имени процесса.

**Параметры:**
```json
{"app": "chrome"}
```

---

### `app_list` — Список запущенных приложений
🟢 safe

Возвращает список активных приложений.

**Параметры:** нет

---

## Инструменты управления окнами

### `window_list` — Список окон
🟢 safe

Возвращает все открытые окна с их заголовками.

---

### `window_control` — Управление окном
🟡 moderate

Управляет конкретным окном.

**Параметры:**
```json
{
  "title": "Chrome",
  "action": "maximize"
}
```

**Доступные action:**
- `focus` — перевести на передний план
- `minimize` — свернуть
- `maximize` — развернуть
- `restore` — восстановить
- `move` — переместить (`x`, `y`)
- `resize` — изменить размер (`width`, `height`)
- `close` — закрыть

---

## Инструменты ввода

### `type_text` — Ввод текста
🟡 moderate

Вводит текст в активное поле ввода.

**Параметры:**
```json
{"text": "Hello, World!", "interval": 0.05}
```

---

### `hotkey` — Горячие клавиши
🟡 moderate

Нажимает комбинацию клавиш.

**Параметры:**
```json
{"keys": ["ctrl", "c"]}
```

**Примеры комбинаций:** `ctrl+c`, `ctrl+v`, `alt+tab`, `win+d`, `ctrl+shift+t`

---

### `click` — Клик мышью
🟡 moderate

Кликает в заданные координаты или на элемент.

**Параметры:**
```json
{"x": 100, "y": 200, "button": "left", "clicks": 1}
```

---

### `scroll` — Прокрутка
🟢 safe

Прокручивает страницу/область.

**Параметры:**
```json
{"x": 500, "y": 400, "direction": "down", "amount": 3}
```

---

## Инструменты экрана

### `screenshot` — Снимок экрана
🟢 safe

Делает скриншот всего экрана, области или конкретного окна.

**Параметры:**
```json
{
  "mode": "fullscreen",
  "save_path": "screenshot.png"
}
```

**Режимы:** `fullscreen`, `window`, `region`

---

## Инструменты буфера обмена

### `clipboard_get` — Чтение буфера
🟢 safe

Возвращает текущее содержимое буфера обмена.

---

### `clipboard_set` — Запись в буфер
🟡 moderate

Помещает текст в буфер обмена.

**Параметры:**
```json
{"text": "текст для копирования"}
```

---

## Медиа-инструменты

### `volume_control` — Управление громкостью
🟡 moderate

Устанавливает системную громкость.

**Параметры:**
```json
{"action": "set", "level": 50}
```

**Доступные action:** `set`, `get`, `mute`, `unmute`

---

### `media_control` — Управление медиа
🟡 moderate

Отправляет медиа-команды системе.

**Параметры:**
```json
{"action": "play_pause"}
```

**Доступные action:** `play_pause`, `next`, `previous`, `stop`

---

## Инструменты процессов

### `process_list` — Список процессов
🟢 safe

Возвращает запущенные процессы с PID, именем и использованием CPU/RAM.

---

### `process_kill` — Завершение процесса
🔴 dangerous

Принудительно завершает процесс по PID или имени.

**Параметры:**
```json
{"pid": 1234}
```

**Защищённые процессы (нельзя завершить):** csrss.exe, lsass.exe, explorer.exe, svchost.exe, winlogon.exe, services.exe

---

## Системная информация

### `system_info` — Информация о системе
🟢 safe

Возвращает текущее состояние системы.

**Возвращает:**
- CPU: использование %, частота, ядра
- RAM: использование, доступно
- GPU: VRAM использование, температура (через GPUtil)
- Диски: использование по дискам

---

## Уведомления

### `notify` — Системное уведомление
🟢 safe

Показывает системное уведомление Windows.

**Параметры:**
```json
{
  "title": "LVCA",
  "message": "Задача выполнена",
  "duration": 5
}
```

---

## Сводная таблица

| Инструмент | Категория | Уровень | Требует DA* |
|------------|-----------|---------|------------|
| `system_cmd` | Система | 🟡 moderate | Нет |
| `file_read` | Система | 🟢 safe | Нет |
| `file_write` | Система | 🟡 moderate | Нет |
| `file_list` | Система | 🟢 safe | Нет |
| `code_gen` | Код | 🟡 moderate | Нет |
| `browser` | Браузер | 🟡 moderate | Нет |
| `vision` | Зрение | 🟢 safe | Нет |
| `app_launch` | Приложения | 🟡 moderate | **Да** |
| `app_close` | Приложения | 🟡 moderate | **Да** |
| `app_list` | Приложения | 🟢 safe | **Да** |
| `window_list` | Окна | 🟢 safe | **Да** |
| `window_control` | Окна | 🟡 moderate | **Да** |
| `type_text` | Ввод | 🟡 moderate | **Да** |
| `hotkey` | Ввод | 🟡 moderate | **Да** |
| `click` | Ввод | 🟡 moderate | **Да** |
| `scroll` | Ввод | 🟢 safe | **Да** |
| `screenshot` | Экран | 🟢 safe | **Да** |
| `clipboard_get` | Буфер | 🟢 safe | **Да** |
| `clipboard_set` | Буфер | 🟡 moderate | **Да** |
| `volume_control` | Медиа | 🟡 moderate | **Да** |
| `media_control` | Медиа | 🟡 moderate | **Да** |
| `process_list` | Процессы | 🟢 safe | **Да** |
| `process_kill` | Процессы | 🔴 dangerous | **Да** |
| `system_info` | Инфо | 🟢 safe | **Да** |
| `notify` | Уведомления | 🟢 safe | **Да** |

*DA = Desktop Agent (:9100) должен быть запущен нативно

---

## Добавление нового инструмента

```python
# services/brain/tools/my_tool.py
from .base import BaseTool, ToolResult

class MyTool(BaseTool):
    name = "my_tool"
    description = """
    Описание инструмента для LLM (что делает, когда использовать).
    Параметры: param1 (str) - описание, param2 (int) - описание.
    """

    async def execute(self, param1: str, param2: int = 0) -> ToolResult:
        try:
            result = do_something(param1, param2)
            return ToolResult(success=True, output=str(result))
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

1. Создать файл `services/brain/tools/my_tool.py`
2. Добавить импорт в `services/brain/tools/__init__.py`
3. Передать экземпляр в `Agent` при инициализации
4. Описание в `description` автоматически попадёт в системный промпт

---

## Безопасность

Desktop Agent работает только на `127.0.0.1` — недоступен извне.

**Аварийная остановка:** Перемести мышь в угол экрана → pyautogui failsafe активируется → все автоматические действия прекращаются.

**Заблокированные команды system_cmd:**
`format`, `del /s /q`, `rmdir /s /q`, `shutdown`, `reg delete`, `netsh`, `sc delete`, `taskkill /f /im`

**Заблокированные пути file_read/write:**
`C:\Windows\System32\`, `C:\Windows\SysWOW64\`, `.ssh\`, `credentials`, `passwords`
