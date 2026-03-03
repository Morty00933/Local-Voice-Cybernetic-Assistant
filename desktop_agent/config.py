"""Desktop Agent configuration."""
from __future__ import annotations

import os
from pathlib import Path

# ── Server ────────────────────────────────────────────────────────
HOST = os.getenv("DESKTOP_AGENT_HOST", "127.0.0.1")
PORT = int(os.getenv("DESKTOP_AGENT_PORT", "9100"))

# ── Screenshots ───────────────────────────────────────────────────
SCREENSHOT_DIR = Path(os.getenv(
    "DESKTOP_SCREENSHOT_DIR",
    str(Path(__file__).resolve().parent.parent / "screenshots"),
))
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ── App registry: friendly name → executable / shortcut name ─────
# Values should be either:
#   - An executable in PATH (notepad, calc, explorer)
#   - A Start Menu shortcut name (Discord, Steam, Telegram)
#   - A full path to .exe
APP_REGISTRY: dict[str, str] = {
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "brave": "brave",
    "yandex": "browser",  # Yandex Browser
    "yandex browser": "browser",
    "yandex-browser": "browser",
    "opera": "opera",
    # Editors / IDEs
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "notepad": "notepad",
    "notepad++": "notepad++",
    "sublime": "subl",
    "pycharm": "pycharm64",
    # System
    "explorer": "explorer",
    "проводник": "explorer",
    "terminal": "wt",
    "cmd": "cmd",
    "powershell": "powershell",
    "calc": "calc",
    "calculator": "calc",
    "калькулятор": "calc",
    "task_manager": "taskmgr",
    "диспетчер задач": "taskmgr",
    "settings": "ms-settings:",
    "настройки": "ms-settings:",
    "control panel": "control",
    "панель управления": "control",
    # Media
    "vlc": "vlc",
    "spotify": "Spotify",
    # Communication
    "telegram": "Telegram",
    "discord": "Discord",
    "slack": "Slack",
    "teams": "ms-teams:",
    "microsoft teams": "ms-teams:",
    "zoom": "Zoom",
    "whatsapp": "WhatsApp",
    # Gaming
    "steam": "steam",
    "epic": "EpicGamesLauncher",
    "epic games": "EpicGamesLauncher",
    # Dev tools
    "git_bash": "git-bash",
    "docker_desktop": "Docker Desktop",
    "docker": "Docker Desktop",
    "postman": "Postman",
}

# ── Safety ────────────────────────────────────────────────────────
MAX_TYPE_LENGTH = 5000  # Max characters for desktop_input type action
PYAUTOGUI_PAUSE = 0.05  # Seconds between pyautogui actions
PYAUTOGUI_FAILSAFE = True  # Mouse to corner aborts
