"""Desktop control tools — proxy to native Desktop Agent."""
from .app_control import AppLaunchTool, AppCloseTool, AppListTool
from .window_mgr import WindowListTool, WindowControlTool
from .input_control import TypeTextTool, HotkeyTool, MouseClickTool, ScrollTool
from .screenshot_tool import ScreenshotTool
from .desktop_info import (
    SystemInfoTool,
    ClipboardGetTool,
    ClipboardSetTool,
    VolumeControlTool,
    MediaControlTool,
    ProcessListTool,
    ProcessKillTool,
    NotifyTool,
)

ALL_DESKTOP_TOOLS = [
    AppLaunchTool(),
    AppCloseTool(),
    AppListTool(),
    WindowListTool(),
    WindowControlTool(),
    TypeTextTool(),
    HotkeyTool(),
    MouseClickTool(),
    ScrollTool(),
    ScreenshotTool(),
    SystemInfoTool(),
    ClipboardGetTool(),
    ClipboardSetTool(),
    VolumeControlTool(),
    MediaControlTool(),
    ProcessListTool(),
    ProcessKillTool(),
    NotifyTool(),
]

__all__ = [
    "AppLaunchTool", "AppCloseTool", "AppListTool",
    "WindowListTool", "WindowControlTool",
    "TypeTextTool", "HotkeyTool", "MouseClickTool", "ScrollTool",
    "ScreenshotTool",
    "SystemInfoTool", "ClipboardGetTool", "ClipboardSetTool",
    "VolumeControlTool", "MediaControlTool",
    "ProcessListTool", "ProcessKillTool", "NotifyTool",
    "ALL_DESKTOP_TOOLS",
]
