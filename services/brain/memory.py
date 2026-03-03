from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system" | "tool"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationMemory:
    """Sliding-window conversation buffer with optional persistence."""

    def __init__(
        self,
        max_turns: int = 20,
        persist_path: Optional[str] = None,
    ):
        self.max_turns = max_turns
        self.persist_path = Path(persist_path) if persist_path else None
        self._messages: List[Message] = []
        self._session_id: str = ""

        if self.persist_path and self.persist_path.exists():
            self._load()

    @property
    def messages(self) -> List[Message]:
        return list(self._messages)

    @property
    def session_id(self) -> str:
        return self._session_id

    @session_id.setter
    def session_id(self, value: str) -> None:
        self._session_id = value

    def add(self, role: str, content: str, **metadata: Any) -> None:
        msg = Message(role=role, content=content, metadata=metadata)
        self._messages.append(msg)

        # Trim to max_turns (keep system messages)
        non_system = [m for m in self._messages if m.role != "system"]
        if len(non_system) > self.max_turns * 2:
            # Keep last max_turns exchanges
            keep = non_system[-(self.max_turns * 2):]
            system = [m for m in self._messages if m.role == "system"]
            self._messages = system + keep

        if self.persist_path:
            self._save()

    def get_context(self, last_n: int | None = None) -> List[Dict[str, str]]:
        msgs = self._messages
        if last_n:
            non_system = [m for m in msgs if m.role != "system"]
            system = [m for m in msgs if m.role == "system"]
            msgs = system + non_system[-last_n:]
        return [{"role": m.role, "content": m.content} for m in msgs]

    def get_text_history(self, last_n: int = 10) -> str:
        recent = [m for m in self._messages if m.role != "system"][-last_n:]
        lines = []
        for m in recent:
            prefix = "User" if m.role == "user" else "Assistant"
            lines.append(f"{prefix}: {m.content}")
        return "\n".join(lines)

    def clear(self) -> None:
        self._messages.clear()
        if self.persist_path:
            self._save()

    def _save(self) -> None:
        if not self.persist_path:
            return
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "session_id": self._session_id,
                "messages": [asdict(m) for m in self._messages],
            }
            self.persist_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Failed to save memory: {e}")

    def _load(self) -> None:
        if not self.persist_path or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text(encoding="utf-8"))
            self._session_id = data.get("session_id", "")
            self._messages = [
                Message(**m) for m in data.get("messages", [])
            ]
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")
            self._messages = []
