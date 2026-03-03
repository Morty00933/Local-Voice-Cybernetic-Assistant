# Desktop Control Examples — Примеры управления ПК

Примеры реального использования Desktop Agent для автоматизации Windows.
Все примеры требуют запущенного Desktop Agent (`make desktop-agent`).

---

## Настройка

```bash
# Убедиться что Desktop Agent работает
make desktop-agent-install   # один раз
make desktop-agent           # запустить в отдельном терминале

# Проверить
curl http://localhost:9100/health
# → {"status": "ok", "tools": [...]}
```

---

## Сценарий 1: Утренний старт

**Запрос:**
```
"Запусти рабочие программы: Chrome, VS Code и Telegram"
```

**Что происходит:**
```
Step 1: [app_launch: chrome]   → Chrome открыт
Step 2: [app_launch: vscode]   → VS Code открыт
Step 3: [app_launch: telegram] → Telegram открыт
```

**Ответ:** "Открыл Chrome, VS Code и Telegram. Рабочее место готово."

---

## Сценарий 2: Организация окон

**Запрос:**
```
"Расположи VS Code слева, Chrome справа"
```

**Что происходит:**
```
Step 1: [window_control: VS Code, move x=0 y=0]
Step 2: [window_control: VS Code, resize width=960 height=1080]
Step 3: [window_control: Chrome, move x=960 y=0]
Step 4: [window_control: Chrome, resize width=960 height=1080]
```

**Ответ:** "VS Code слева, Chrome справа. Разрешение 1920×1080, каждое окно занимает половину."

---

## Сценарий 3: Копирование и вставка

**Запрос:**
```
"Скопируй текст из буфера обмена, переведи его на английский и вставь обратно"
```

**Что происходит:**
```
Step 1: [clipboard_get]
        → "Привет, как дела?"
Step 2: [LLM перевод]
        → "Hello, how are you?"
Step 3: [clipboard_set: "Hello, how are you?"]
```

**Ответ:** "Перевёл и положил в буфер: 'Hello, how are you?'. Теперь можешь вставить Ctrl+V."

---

## Сценарий 4: Скриншот и анализ

**Запрос:**
```
"Сделай скриншот и скажи что на экране"
```

**Что происходит:**
```
Step 1: [screenshot: fullscreen → screen.png]
Step 2: [vision: "Опиши что на экране" + screen.png]
        → "На экране открыт VS Code с Python файлом agent.py.
           Слева — файловый эксплорер с проектом LVCA.
           В терминале внизу видны зелёные строки логов."
```

---

## Сценарий 5: Автоматическое заполнение формы

**Запрос:**
```
"Перейди на форму регистрации и заполни имя 'Иван', фамилию 'Петров'"
```

**Что происходит:**
```
Step 1: [browser: open https://example.com/register]
Step 2: [screenshot] → найти поля формы
Step 3: [click: поле "Имя"]
Step 4: [type_text: "Иван"]
Step 5: [click: поле "Фамилия"]
Step 6: [type_text: "Петров"]
```

> Примечание: LVCA не вводит пароли, финансовые данные и другую чувствительную информацию.

---

## Сценарий 6: Управление громкостью по контексту

**Запросы:**
```
"Приглуши — начинается встреча"
→ [volume_control: set 20] Громкость снижена до 20%

"Встреча закончилась, верни звук"
→ [volume_control: set 65] Громкость возвращена до 65%

"Поставь Spotify на паузу"
→ [media_control: play_pause] Музыка на паузе

"Следующий трек"
→ [media_control: next] Следующий трек включён
```

---

## Сценарий 7: Мониторинг системы

**Запрос:**
```
"Есть ли процессы которые сжирают память?"
```

**Что происходит:**
```
Step 1: [process_list]
        → chrome.exe  PID:1234  CPU:2.1%  RAM:1.2 GB
          code.exe    PID:5678  CPU:0.8%  RAM:450 MB
          discord.exe PID:9012  CPU:0.1%  RAM:380 MB
          ...
Step 2: [LLM анализирует]
```

**Ответ:** "Самый прожорливый процесс — Chrome (1.2 GB RAM, 3 процесса). Если нужно — могу закрыть Chrome."

---

## Сценарий 8: Горячие клавиши для продуктивности

```
"Сохрани текущий файл"
→ [hotkey: ctrl+s]

"Отмени последнее действие"
→ [hotkey: ctrl+z]

"Открой новую вкладку в браузере"
→ [hotkey: ctrl+t]

"Закрой текущую вкладку"
→ [hotkey: ctrl+w]

"Выдели весь текст и скопируй"
→ [hotkey: ctrl+a] → [hotkey: ctrl+c]

"Переключись на следующее окно"
→ [hotkey: alt+tab]

"Покажи рабочий стол"
→ [hotkey: win+d]
```

---

## Сценарий 9: Рабочий процесс разработчика

**Запрос:**
```
"Я написал код, запусти тесты и скажи результат"
```

**Что происходит:**
```
Step 1: [window_control: VS Code, focus]   → переключаемся в VS Code
Step 2: [hotkey: ctrl+grave]               → открываем терминал
Step 3: [type_text: "python -m pytest --tb=short\n"]
Step 4: [screenshot: window=VS Code]       → ждём и делаем скриншот
Step 5: [vision: "Прочитай результаты тестов"]
        → "5 passed, 1 failed. Ошибка в test_agent.py:45..."
```

---

## Сценарий 10: Уведомление и таймер

**Запрос:**
```
"Покажи уведомление что пора сделать перерыв"
```

**Что происходит:**
```
Step 1: [notify: title="LVCA", message="Время сделать перерыв! Вы работаете уже 90 минут."]
```

---

## API-вызовы Desktop Agent напрямую

Desktop Agent также доступен напрямую через HTTP (без Brain):

```bash
# Запуск приложения
curl -X POST http://localhost:9100/api/apps/launch \
  -H "Content-Type: application/json" \
  -d '{"name": "chrome"}'

# Скриншот
curl http://localhost:9100/api/screenshot \
  --output screenshot.png

# Системная информация
curl http://localhost:9100/api/system_info

# Установить громкость
curl -X POST http://localhost:9100/api/media/volume \
  -H "Content-Type: application/json" \
  -d '{"level": 50}'

# Нажать комбинацию клавиш
curl -X POST http://localhost:9100/api/input/hotkey \
  -H "Content-Type: application/json" \
  -d '{"keys": ["ctrl", "s"]}'

# Напечатать текст
curl -X POST http://localhost:9100/api/input/type \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from LVCA!", "interval": 0.05}'

# Список окон
curl http://localhost:9100/api/windows/list

# Фокус на окно
curl -X POST http://localhost:9100/api/windows/control \
  -H "Content-Type: application/json" \
  -d '{"title": "Visual Studio Code", "action": "focus"}'

# Уведомление
curl -X POST http://localhost:9100/api/notify \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "message": "Hello from LVCA"}'
```

---

## Безопасность при автоматизации

**Failsafe:** Если что-то пошло не так — переведи мышь в верхний левый угол экрана. pyautogui остановит все автоматические действия.

**Чего LVCA не сделает:**
- Не завершит системные процессы (csrss, lsass, explorer, svchost)
- Не выполнит `format`, `shutdown`, `del /s /q`
- Не введёт пароли и финансовые данные
- Не изменит системные файлы Windows

**Что проверять перед автоматизацией:**
```bash
# Убедиться что Desktop Agent запущен с нужными правами
curl http://localhost:9100/health
# → {"status": "ok"}
```
