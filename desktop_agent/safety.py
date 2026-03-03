"""Safety layer for Desktop Agent actions."""
from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# Actions that are read-only / safe — no confirmation needed
SAFE_ACTIONS = frozenset({
    "screenshot", "window_list", "clipboard_get", "volume_get",
    "process_list", "system_info", "app_list",
})

# Actions that modify state but are generally safe
MODERATE_ACTIONS = frozenset({
    "app_launch", "window_focus", "window_minimize", "window_maximize",
    "window_restore", "window_resize", "window_move",
    "type_text", "hotkey", "click", "scroll", "mouse_move",
    "clipboard_set", "volume_set", "volume_mute",
    "media_play_pause", "media_next", "media_prev",
    "notify",
})

# Dangerous actions — log a warning
DANGEROUS_ACTIONS = frozenset({
    "process_kill", "app_close", "window_close",
})

# Patterns that should NEVER be executed
BLOCKED_PATTERNS = [
    re.compile(r"format\s+[a-zA-Z]:", re.IGNORECASE),
    re.compile(r"del\s+/[sfq]", re.IGNORECASE),
    re.compile(r"rm\s+-rf?\s+/", re.IGNORECASE),
    re.compile(r"shutdown\s", re.IGNORECASE),
    re.compile(r"taskkill.*(?:csrss|lsass|winlogon|svchost|system)", re.IGNORECASE),
    re.compile(r"reg\s+delete", re.IGNORECASE),
    re.compile(r"bcdedit", re.IGNORECASE),
    re.compile(r"diskpart", re.IGNORECASE),
]

# System processes that cannot be killed
PROTECTED_PROCESSES = frozenset({
    "csrss.exe", "lsass.exe", "winlogon.exe", "svchost.exe",
    "system", "smss.exe", "services.exe", "wininit.exe",
    "dwm.exe", "explorer.exe",
})


def is_blocked_command(command: str) -> bool:
    """Check if a command matches any blocked pattern."""
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(command):
            logger.warning("BLOCKED dangerous command: %s", command)
            return True
    return False


def is_protected_process(name: str) -> bool:
    """Check if a process name is system-critical."""
    return name.lower() in PROTECTED_PROCESSES


def classify_action(action: str) -> str:
    """Classify an action's safety level."""
    if action in SAFE_ACTIONS:
        return "safe"
    if action in MODERATE_ACTIONS:
        return "moderate"
    if action in DANGEROUS_ACTIONS:
        return "dangerous"
    return "unknown"
