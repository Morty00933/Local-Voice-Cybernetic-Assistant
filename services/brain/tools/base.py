from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ToolResult:
    success: bool
    output: str
    data: Dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        ...

    def schema(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description}
