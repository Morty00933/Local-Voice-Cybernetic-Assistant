from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class Embeddings(ABC):
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]: ...


class LLM(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str: ...


class VectorStore(ABC):
    @abstractmethod
    def upsert(
        self,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> None: ...

    @abstractmethod
    def search(self, query: List[float], top_k: int) -> List[Tuple[Dict[str, Any], float]]: ...
